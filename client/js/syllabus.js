'use strict';

var app = angular.module('syllabus', [
    'ui.router',
    'ui.bootstrap',
    'ui-notification',
    'ngTagsInput',
    'ngDialog',
    'ngSanitize',
    'ui.select',
    'angular.filter',
    'angularUtils.directives.dirPagination'
]);


app.constant('config', {
    // topics+units index pages
    itemsPerPage: 20
});


// show an error on not authed / not logged in / incorrect permissions
app.factory('authCheck', ['$q', '$injector', function($q, $injector) {
    var sessionRecoverer = {
        responseError: function(response) {
            if (response.status == 401) {
                $injector.get('Notification').error("Not logged in.");
            }
            if (response.status == 403) {
                $injector.get('Notification').error("You are not authorised to do that.");
            }
            if (response.status == 500) {
                $injector.get('Notification').error("Unkown server error, please try again.");
            }
            return $q.reject(response);
        }
    };
    return sessionRecoverer;
}]);


app.config(function (NotificationProvider, $httpProvider) {
    NotificationProvider.setOptions({
        positionX: 'left',
        positionY: 'bottom'
    });

    $httpProvider.interceptors.push('authCheck');
});


app.factory('wp', function ($http, api) {
    return {
        suggestions: function suggestions(search) {
            return $http.jsonp('//en.wikipedia.org/w/api.php', {
                params: {
                    callback: 'JSON_CALLBACK', // So that JSONP works correctly
                    action: 'opensearch',
                    format: 'json',
                    search: search
                }
            }).then(function (response) {
                return response.data[1];
            });
        },

        search: function search(_search) {
            return $http.jsonp('//en.wikipedia.org/w/api.php', {
                params: {
                    callback: 'JSON_CALLBACK', // So that JSONP works correctly
                    format: 'json',
                    action: 'query',
                    list: 'search',
                    srsearch: _search,
                    srprop: 'redirecttitle|sectiontitle'
                }
            });
        },

        basicInfo: function basicInfo(name) {
            return $http.jsonp('//en.wikipedia.org/w/api.php', {
                params: {
                    action: 'query',
                    callback: 'JSON_CALLBACK', // So that JSONP works correctly
                    format: 'json',
                    titles: name,
                    prop: 'extracts|categories',
                    exintro: true,
                    explaintext: true,
                    redirects: true,
                    clshow: '!hidden'
                }
            });
        },

        additionalInfo: function additionalInfo(inst, dept, searchResult) {
            var titles = searchResult.pages.map(function (page) {
                return page.title;
            });
            return $http.jsonp('//en.wikipedia.org/w/api.php', {
                params: {
                    action: 'query',
                    callback: 'JSON_CALLBACK', // So that JSONP works correctly
                    format: 'json',
                    indexpageids: true,
                    titles: titles.join('|'),
                    prop: 'extracts|categories',
                    exintro: true,
                    exlimit: 'max',
                    exsentences: 1,
                    explaintext: true,
                    cllimit: 'max',
                    redirects: true
                }
            }).then(function (response) {
                // Re-map by title
                var pageInfo = {};
                response.data.query.pageids.forEach(function (pageId) {
                    var p = response.data.query.pages[pageId];
                    pageInfo[p.title] = p;
                });

                // Attach additional data to results
                searchResult.pages.forEach(function (page) {
                    page.extract = pageInfo[page.title].extract;

                    // Mark disambiguation pages
                    page.isDisambiguation = pageInfo[page.title].categories.some(function (category) {
                        return category.title === "Category:All disambiguation pages";
                    });
                });

                // Filter out disambiguation pages
                var filteredPages = searchResult.pages.filter(function (page) {
                    return !page.isDisambiguation;
                });

                searchResult.numDisambiguationPages = searchResult.pages.length - filteredPages.length;
                searchResult.pages = filteredPages;

                // Fetch additional info from our API
                api.additionalInfo(inst, dept, searchResult);
            });
        }
    };
});


app.factory('api', function ($http, $stateParams, $sce) {
    return (// FIXME: don't use stateParams here
        {
            additionalInfo: function additionalInfo(inst, dept, searchResult) {
                var titles = searchResult.pages.map(function (page) {
                    return page.title;
                });
                return $http.get('api/' + inst + '/' + dept + '/unit_topics', {
                    params: {
                        topic_name: titles.join('|'),
                        embed: 'topic,unit'
                    }
                }).then(function (response) {
                    var meta = new Map();

                    response.data.unit_topics.forEach(function (unit_topic) {
                        var topic = unit_topic.topic,
                            unit = unit_topic.unit;

                        // Make sure topic is already in the map
                        if (!meta.has(topic.name)) {
                            meta.set(topic.name, {units: [], topicID: topic.id});
                        }

                        meta.get(topic.name).units.push(unit.code);
                    });

                    searchResult.pages.forEach(function (page) {
                        if (meta.has(page.title)) {
                            page.units = meta.get(page.title).units;
                            page.id = meta.get(page.title).topicID;
                            // TODO: remove unit_code from units
                            page.isAdded = page.units.indexOf($stateParams.unit_code) !== -1;
                        } else {
                            page.isAdded = false;
                        }
                    });
                });
            },


            addUnitTopic: function addUnitTopic(inst, dept, unitCode, topicName) {
                return $http.post('api/' + inst + '/' + dept + '/unit_topics/add', {
                    unit_code: unitCode,
                    topic_name: topicName
                });
            },


            addCustomUnitTopic: function addCustomUnitTopic(inst, dept, unitCode, topicName, topicDescr, topicKeywords) {
                return $http.post('api/' + inst + '/' + dept + '/unit_topics/add', {
                    unit_code: unitCode,
                    topic_name: topicName,
                    topic_description: topicDescr,
                    topic_keywords: topicKeywords
                });
            },


            updateUnitTopic: function updateUnitTopic(inst, dept, unitTopic) {
                return $http.post('api/'+inst+'/'+dept+'/unit_topics/update', unitTopic);
            },


            removeUnitTopic: function removeUnitTopic(inst, dept, id) {
                return $http.post('api/'+inst+'/'+dept+'/unit_topics/remove', {
                    unit_topic_id: id
                });
            },


            fetchUnit: function fetchUnit(unitCode, inst, dept) {
                return $http.get('api/' + inst + '/' + dept + '/unit/' + unitCode);
            },
            fetchTopic: function fetchTopic(topicId, inst, dept) {
                return $http.get('api/' + inst + '/' + dept + '/topic/' + topicId);
            },


            fetchUnitTopics: function fetchUnitTopics(inst, dept, unitCode) {
                return $http.get('api/' + inst + '/' + dept + '/unit_topics', {
                    params: {
                        unit_code: unitCode,
                        embed: 'topic,contexts'
                    }
                }).then(function (response) {
                    return response.data.unit_topics;
                });
            },


            fetchGraph: function fetchGraph(url) {
                return $http.get(url).then(function (response) {
                    var data = response.data;
                    data += "<script>enableSVGInteraction()</script>"; // FIXME: hacky
                    return $sce.trustAsHtml(data);
                });
            },


            doLogin: function doLogin(user, pass, inst, dept) {
                return $http.post('api/login', {
                    user: user,
                    pass: pass,
                    institution: inst,
                    department: dept
                });
            },
            doLogout: function doLogout() {
                return $http.get('api/logout');
            },


            addUnit: function addUnit(inst, dept, unitCode, unitName, unitLevel) {
                return $http.post('api/' + inst + '/' + dept + '/unit/add', {
                    code: unitCode,
                    name: unitName,
                    level: unitLevel
                });
            },
            updateUnit: function updateUnit(inst, dept, unit) {
                return $http.post('api/' + inst + '/' + dept + '/unit/update', unit);
            },
            removeUnit: function removeUnit(inst, dept, id) {
                return $http.post('api/'+inst+'/'+dept+'/unit/remove', {
                    id: id
                });
            },


            bulkAddUnits: function bulkAddUnits(inst, dept, data) {
                var units = [];
                data.data.forEach(function(u) {
                    units.push({
                        "code": u[data.code],
                        "level": u[data.level],
                        "name": u[data.name]
                    });
                });
                return $http.post('api/'+inst+'/'+dept+'/admin/bulkaddunits', {units: units});
            },


            fetchUnits: function fetchUnits(inst, dept) {
                return $http.get('api/' + inst + '/' + dept + '/units');
            },
            fetchUnitCount: function fetchUnitCount(inst, dept) {
                return $http.get('api/' + inst + '/' + dept + '/unitcount');
            },
            fetchUnitsLimit: function fetchUnitsLimit(inst, dept, items, offset) {
                return $http.get('api/' + inst + '/' + dept + '/units/' + items + '/' + offset);
            },
            fetchTopics: function fetchUnits(inst, dept) {
                return $http.get('api/' + inst + '/' + dept + '/topics');
            },
            fetchTopicCount: function fetchTopicCount(inst, dept) {
                return $http.get('api/' + inst + '/' + dept + '/topiccount');
            },
            fetchTopicsLimit: function fetchUnitsLimit(inst, dept, items, offset) {
                return $http.get('api/' + inst + '/' + dept + '/topics/' + items + '/' + offset);
            },


            fetchInstitutionsAdmin: function fetchInstitutions() {
                return $http.get('api/admin/institutions');
            },
            fetchDepartmentsAdmin: function fetchDepartments(inst) {
                return $http.get('api/'+inst+'/admin/departments');
            },


            getInstitutionInfo: function getInstitutionInfo(inst) {
                return $http.get('api/'+inst);
            },


            fetchInstitutions: function fetchInstitutions() {
                return $http.get('api/institutions/');
            },
            fetchDepartments: function fetchDepartments(inst) {
                return $http.get('api/'+inst+'/departments');
            },


            fetchDepartmentsGrouped: function fetchDepartmentsGrouped() {
                return $http.get('api/departments_group');
            },


            addUser: function addUser(username, password, inst, dept) {
                return $http.post('api/'+inst+'/'+dept+'/admin/adduser', {
                    username: username,
                    password: password
                });
            },


            addInstitution: function addInstitution(name, uri, user, pass) {
                return $http.post('api/admin/addinstitution', {
                    name: name,
                    uri: uri,
                    username: user,
                    password: pass
                });
            },
            updateInstitution: function updateInstitution(inst) {
                return $http.post('api/admin/updateinstitution', inst);
            },
            removeInstitution: function removeInstitution(id) {
                return $http.post('api/admin/removeinstitution', {
                    id: id
                });
            },


            addDepartment: function addDepartment(inst, name, uri) {
                return $http.post('api/'+inst+'/admin/adddepartment', {
                    name: name,
                    uri: uri
                });
            },
            updateDepartment: function updateDepartment(inst, dept) {
                return $http.post('api/'+inst+'/admin/updatedepartment', dept);
            },
            removeDepartment: function removeDepartment(inst, id) {
                return $http.post('api/'+inst+'/admin/removedepartment', {
                    id: id
                });
            },


            get_admin_controls: function get_admin_controls() {
                return $http.get('api/admin');
            },


            get_filtered_topics_limit: function get_filtered_topics(inst, dept, filters, items, offset) {
                var a = {'include': [], 'exclude': []}
                for (var i in filters) {
                    if (filters[i].is) {
                        a.include.push({'taught': filters[i].taught, 'levels': filters[i].levels});
                    } else {
                        a.exclude.push({'taught': filters[i].taught, 'levels': filters[i].levels});
                    }
                }
                return $http.post('api/'+inst+'/'+dept+'/topics/filter/'+items+'/'+offset, {
                    'include': a.include,
                    'exclude': a.exclude
                });
            }
        }
    );
});


app.controller('units', function ($scope, $stateParams, api, Notification, ngDialog, config) {
    $scope.config = config;

    $scope.totalUnits = 0;

    $scope.fetchUnitsLimit = function(offset) {
        api.fetchUnitsLimit($stateParams.inst_uri, $stateParams.dept_uri, config.itemsPerPage, offset).success(function (data) {
            $scope.totalUnits = data.total;
            $scope.units = data.units;
        });
    }
    $scope.fetchUnitsLimit(0);


    $scope.edit = function (unit) {
        unit.isEditing = true;
    };


    $scope.remove = function (unit) {
        ngDialog.openConfirm({template: 'tpl/confirm.html'}).then(
            function (value) {
                api.removeUnit($stateParams.inst_uri, $stateParams.dept_uri, unit.id).then(function () {
                    console.log("unit " + unit.code + " removed");
                    Notification.success('Unit removed');
                    var i = $scope.units.indexOf(unit);
                    $scope.units.splice(i, 1);
                });
            }
        );
    };


    $scope.save = function (unit) {
        api.updateUnit($stateParams.inst_uri, $stateParams.dept_uri, unit).then(function () {
            unit.isEditing = false;
            Notification.success('Topic saved');
        });
    };


    $scope.cancel = function (unitTopic) {
        unitTopic.isEditing = false;
    };


    $scope.add = function() {
        ngDialog.openConfirm({template: 'tpl/add_unit.html', data: $scope}).then(
            function(value) {
                api.addUnit($stateParams.inst_uri, $stateParams.dept_uri, $scope.code, $scope.name, $scope.level).then(
                    function(success) {
                        if (success.data == 0) {
                            Notification.error("fail");
                        } else if (success.data == 1) {
                            Notification.success("Added new unit");
                            // just refetch units, its way easier
                            api.fetchUnits($stateParams.inst_uri, $stateParams.dept_uri)
                                .success(function (data) {
                                $scope.units = data.units;
                            });
                        } else {
                            Notification.error("unknown error");
                        }
                    },
                    function(error) {
                        Notification.error(error);
                    }
                )
            },
            function(value) {
                //Cancel
            }
        );
    }
});

app.controller('topics', function($scope, $stateParams, $templateRequest, $compile, api, config, wp) {
    $scope.config = config;
    $scope.wpSuggestions = wp.suggestions;
    $scope.totalTopics = 0;


    $scope.fetchTopicsLimit = function(offset) {
        $scope.isQuery = false;
        api.fetchTopicsLimit($stateParams.inst_uri, $stateParams.dept_uri, config.itemsPerPage, offset).success(function (data) {
            $scope.totalTopics = data.total;
            $scope.topics = data.topics.map(function(topic) {
                return {
                    title: topic.name,
                    id: topic.id,
                    units: topic.unit_topics.map(function(unit) {
                        return unit.unit.code;
                    })
                };
            });
        });
    };
    $scope.fetchTopicsLimit(0);


    $scope.wpSearch = function () {
        $scope.topics__currentPage = 1;
        if ($scope.query) {
            wp.search($scope.query).then(function (response) {
                $scope.searchResult = { pages: response.data.query.search };

                wp.additionalInfo($stateParams.inst_uri, $stateParams.dept_uri, $scope.searchResult);
                $scope.topics = $scope.searchResult.pages;
            });
            $scope.totalTopics = 0;
        } else {
            $scope.fetchTopicsLimit(0);
        }
    };


    $scope.querylines = [];
    $scope.addQueryLine = function() {
        $scope.querylines.push({is: true});
        // init bootstrap select
        setTimeout(function() {$('.selectpicker').selectpicker()}, 1);
    };

    $scope.removeQueryLine = function(id) {
        $scope.querylines.splice(id, 1);
    };

    $scope.submitQuery = function(offset) {
        $scope.isQuery = true;

        for (var i in $scope.querylines) {
            if ($scope.querylines.levels) {
                $scope.querylines[i].levels =
                    $scope.querylines[i].levels.replace(/ /g,',').split(',').map(Number);
            }
        }

        api.get_filtered_topics_limit($stateParams.inst_uri, $stateParams.dept_uri,
                $scope.querylines, config.itemsPerPage, offset).success(function (data) {

            $scope.totalTopics = data.total;
            $scope.topics = data.topics.map(function(topic) {
                return {
                    title: topic.name,
                    id: topic.id,
                    units: topic.unit_topics.map(function(unit) {
                        return unit.unit.code;
                    })
                };
            });
        });
    };

    $scope.getNextPage = function(offset) {
        if ($scope.isQuery) {
            $scope.submitQuery(offset);
        } else {
            $scope.fetchTopicsLimit(offset);
        }
    }
});

app.controller('unit', function (api, $scope, $http, $stateParams) {
    var unitCode = $stateParams.unit_code;

    api.fetchUnit(unitCode, $stateParams.inst_uri, $stateParams.dept_uri).success(function (data) {
        $scope.unit = data.unit;
        $scope.unitLoaded = true;
    });
});

app.controller('topic', function (api, $scope, $http, $stateParams, wp) {
    var topicId = $stateParams.topic_id;
    $scope.inst_uri = $stateParams.inst_uri;
    $scope.dept_uri = $stateParams.dept_uri;

    if (topicId) {
        api.fetchTopic(topicId, $stateParams.inst_uri, $stateParams.dept_uri).success(function (data) {
            $scope.topic = data.topic;

            for (var category of $scope.topic.categories) {
                category.url = encodeURI("http://en.wikipedia.org/wiki/"
                    + category.name);
                // remove Category: from name
                category.name = category.name.split(":").pop();
            }

            wp.basicInfo($scope.topic.name).then(function (result) {
                for (var page in result.data.query.pages) {
                    $scope.info = result.data.query.pages[page];
                    $scope.info.link = encodeURI("http://en.wikipedia.org/wiki/"
                        + result.data.query.pages[page].title);
                    break;
                }
            });
            $scope.topicLoaded = true;
            $scope.exists = true;
        });
    } else {
        $scope.topic = { name: "Topic does not belong to any units" };
        $scope.topicLoaded = true;
    }
});


app.controller('unit_topics', function ($scope, $http, $stateParams, Notification, api) {
    var unitCode = $stateParams.unit_code;

    api.fetchUnitTopics($stateParams.inst_uri, $stateParams.dept_uri, unitCode).then(function (unitTopics) {
        $scope.unit_topics = unitTopics;
        var topics = unitTopics.map(function (item) {
            return item.topic;
        });
        $scope.context_search = function (query) {
            // Return topics which start with query
            var regExp = new RegExp('^' + query, 'i');
            return topics.filter(function (topic) {
                return regExp.test(topic.name);
            });
        };
        $scope.contentLoaded = true;
    });

    $scope.edit = function (unitTopic) {
        unitTopic.isEditing = true;
    };

    $scope.remove = function (unitTopic) {
        api.removeUnitTopic($stateParams.inst_uri, $stateParams.dept_uri, unitTopic.id).then(function () {
            Notification.success('Topic removed');
            // Re-fetch the list of topics
            // TODO: could just remove unitTopic from $scope.unit_topics?
            api.fetchUnitTopics($stateParams.inst_uri, $stateParams.dept_uri, unitCode).then(function (unitTopics) {
                $scope.unit_topics = unitTopics;
            });
        });
    };

    $scope.save = function (unitTopic) {
        api.updateUnitTopic($stateParams.inst_uri, $stateParams.dept_uri, unitTopic).then(function () {
            unitTopic.isEditing = false;
            Notification.success('Topic saved');
        });
    };

    $scope.cancel = function (unitTopic) {
        unitTopic.isEditing = false;
    };
});

app.controller('custom_topic', function ($scope, $stateParams, $state, api, Notification) {

    $scope.addTopic = function () {
        api.addCustomUnitTopic($stateParams.inst_uri, $stateParams.dept_uri, $scope.unit.code, $scope.name, $scope.description, $scope.keywords).then(function () {
            $state.go('unit.topics');
            Notification.success('Topic added');
        });
    };
});

app.controller('topic_search', function ($scope, $stateParams, wp, api, Notification) {
    $scope.wpSuggestions = wp.suggestions;

    $scope.wpSearch = function () {
        wp.search($scope.query).then(function (response) {
            $scope.searchResult = { pages: response.data.query.search };

            // Fetch additional info
            wp.additionalInfo($stateParams.inst_uri, $stateParams.dept_uri, $scope.searchResult);
        });
    };

    $scope.addTopic = function (topicName) {
        api.addUnitTopic($stateParams.inst_uri, $stateParams.dept_uri, $scope.unit.code, topicName).then(function () {
            Notification.success('Topic added');
            wp.additionalInfo($stateParams.inst_uri, $stateParams.dept_uri, $scope.searchResult);
        });
    };
});

// Makes the element fill the rest of the screen
app.directive('fillScreenHeight', function () {
    return {
        link: function link(scope, element, _) {
            $(window).resize(function () {
                element.height($(window).height() - element.offset().top);
                // TODO: reset svg-pan-zoom
            });
            $(window).resize(); // Trigger initial resize
        }
    };
});

app.controller('main_graph', function ($scope, $stateParams, api) {
    api.fetchGraph('api/' + $stateParams.inst_uri + '/' + $stateParams.dept_uri + '/graph').then(function (svg) {
        $scope.svg = svg;
    });
});

app.controller('unit_graph', function ($scope, $stateParams, api) {
    var unitCode = $stateParams.unit_code;

    $scope.unitCode = unitCode;

    api.fetchGraph('api/' + $stateParams.inst_uri + '/' + $stateParams.dept_uri + '/graph/unit/' + unitCode).then(function (svg) {
        $scope.svg = svg;
    });
});

app.controller('topic_graph', function ($scope, $stateParams, api) {
    var topicId = $stateParams.topic_id;

    api.fetchGraph('api/' + $stateParams.inst_uri + '/' + $stateParams.dept_uri + '/graph/topic/' + topicId).then(function (svg) {
        $scope.svg = svg;
    });
});

app.controller('category_graph', function ($scope, $stateParams, api) {
    var categoryId = $stateParams.category_id;

    api.fetchGraph('api/' + $stateParams.inst_uri + '/' + $stateParams.dept_uri + '/graph/category/' + categoryId).then(function (svg) {
        $scope.svg = svg;
    });
});

app.controller('dept_list_group', function ($scope, $stateParams, ngDialog, api, Notification) {
    $scope.stopevent = function($event) {
        if ($event.stopPropagation) $event.stopPropagation();
        if ($event.preventDefault) $event.preventDefault();
        $event.cancelBubble = true;
        $event.returnValue = false;
    }

    api.fetchDepartmentsGrouped().success(function (data) {
        $scope.institutions = data.institutions;
        if (data.institutions.length < 0) {
            $scope.departments = data.institutions[0].departments;
        }
        $scope.contentLoaded = true;
    });

    $scope.edit = function (object, $event) {
        $scope.stopevent($event);
        object.isEditing = true;
    };

    $scope.remove_dep = function (institution, department, $event) {
        $scope.stopevent($event);
        ngDialog.openConfirm({template: 'tpl/confirm.html'}).then(
            function (value) {
                api.removeDepartment(institution.uri, department.id).then(function () {
                    console.log("department " + department.name + " removed");
                    Notification.success('Department removed');
                    var i = institution.departments.indexOf(department);
                    institution.departments.splice(i, 1);
                });
            }
        );
    };
    $scope.remove_ins = function (institution, $event) {
        $scope.stopevent($event);
        ngDialog.openConfirm({template: 'tpl/confirm.html'}).then(
            function (value) {
                api.removeInstitution(institution.id).then(function () {
                    console.log("institution " + institution.name + " removed");
                    Notification.success('Institution removed');
                    var i = $scope.institutions.indexOf(institution);
                    $scope.institutions.splice(i, 1);
                });
            }
        );
    };

    $scope.save_dep = function (institution, department, $event) {
        $scope.stopevent($event);
        api.updateDepartment(institution.uri, department).then(function () {
            department.isEditing = false;
            Notification.success('Department saved');
        });
    };
    $scope.save_ins = function (institution, $event) {
        $scope.stopevent($event);
        api.updateInstitution(institution).then(function () {
            institution.isEditing = false;
            Notification.success('Institution saved');
        });
    };

    $scope.cancel = function (object, $event) {
        $scope.stopevent($event);
        object.isEditing = false;
    };

    $scope.add_dep = function(institution) {
        ngDialog.openConfirm({template: 'tpl/add_department.html', data: $scope}).then(
            function(value) {
                api.addDepartment(institution.uri, $scope.name, $scope.uri).then(
                    function(success) {
                        if (success.data == 0) {
                            Notification.error("fail");
                        } else if (success.data == 1) {
                            Notification.success("Added new department");
                            api.fetchDepartmentsGrouped().success(function (data) {
                                $scope.departments = data.institutions[0].departments;
                                $scope.institutions = data.institutions;
                            });
                        } else {
                            Notification.error("unknown error");
                        }
                    },
                    function(error) {
                        Notification.error(error);
                    }
                )
            },
            function(value) {
                //Cancel
            }
        );
    }
    $scope.add_ins = function() {
        ngDialog.openConfirm({template: 'tpl/add_institution.html', data: $scope}).then(
            function(value) {
                api.addInstitution($scope.name, $scope.uri, $scope.user, $scope.pass).then(
                    function(success) {
                        if (success.data == 0) {
                            Notification.error("fail");
                        } else if (success.data == 1) {
                            Notification.success("Added new institution");
                            api.fetchDepartmentsGrouped().success(function (data) {
                                $scope.departments = data.institutions[0].departments;
                                $scope.institutions = data.institutions;
                            });
                        } else {
                            Notification.error("unknown error");
                        }
                    },
                    function(error) {
                        Notification.error(error);
                    }
                )
                $scope.user = "";
                $scope.pass = "";
            },
            function(value) {
                //Cancel
                $scope.user = "";
                $scope.pass = "";
            }
        );
    }
});

app.controller('dept_list', function ($scope, $stateParams, api) {

    api.getInstitutionInfo($stateParams.inst_uri).success(function(data) {
        $scope.institution = data;
    });

    api.fetchDepartments($stateParams.inst_uri).success(function (data) {
        $scope.departments = data.departments;
    });
});

app.controller('admin', function ($scope, $stateParams, $templateRequest, $compile, api, Notification, ngDialog) {
    $scope.where = {};

    $scope.populate_insts = function() {
        api.fetchInstitutions().then(function(result) {
            $scope.where.insts = result.data.institutions;
        });
    }

    $scope.populate_depts= function(inst) {
        api.fetchDepartments(inst).then(function(result) {
            $scope.where.depts = result.data.departments;
        });
    }

    api.get_admin_controls().then(function(result) {
        $.each(result.data, function(title, file) {
            $templateRequest('tpl/admin/' + file + '.html').then(function(html){
                var control = angular.element("<form ng-controller='admin_submit as ctrl'></form>");
                control.append("<legend>"+title+"</legend>")
                control.append(html);
                $('#controls').append(control);
                $compile(control)($scope);
            });
        });

    });

});

app.controller('admin_submit', function ($scope, $stateParams, api, Notification, ngDialog) {
    function get_inst_uri(ctrl) {
        if ($scope.ctrl.instsel === undefined) {
            if ($stateParams.inst_uri === undefined) {
                Notification.error("Enter institution");
                return null;
            } else {
                return $stateParams.inst_uri;
            }
        } else {
            return $scope.ctrl.instsel.uri;
        }
    }

    function get_dept_uri() {
        if ($scope.ctrl.deptsel === undefined) {
            if ($stateParams.dept_uri === undefined) {
                Notification.error("Enter department");
                return null;
            } else {
                return $stateParams.dept_uri;
            }
        } else {
            return $scope.ctrl.deptsel.uri;
        }
    }

    $scope.doaddinstitution = function() {
        api.addInstitution($scope.addinstitution.name, $scope.addinstitution.uri,
                $scope.addinstitution.username, $scope.addinstitution.password).then(function() {
            Notification.success('Institution added');
        });
    }

    $scope.doadddepartment = function() {
        var insturi = get_inst_uri();

        if (insturi) {
            api.addDepartment(insturi, $scope.adddepartment.name, $scope.adddepartment.uri).then(function() {
                Notification.success('Department added');
            });
        }
    }

    $scope.adduser = function() {
        var insturi = get_inst_uri();
        var depturi = get_dept_uri();

        if (insturi && depturi) {
            api.addUser($scope.adduser.username, $scope.adduser.password,
                insturi, depturi).then(function() {
                Notification.success('User added');
            });
        }
    }

    function showForm(data, header) {
        $scope.newunits = {data: data}
        ngDialog.openConfirm({
            template: 'csvPopup',
            data: {data: data[0], header: header, scope: $scope}
        }).then(function(value) {
            console.log($scope.department);
            var insturi = get_inst_uri();
            var depturi = get_dept_uri();

            if (insturi && depturi) {
                api.bulkAddUnits(insturi, depturi, $scope.newunits).then(
                    function(success) {
                        Notification.success("Added units");
                    }, function(error) {
                        Notification.error("Error: nothing changed.");
                    }
                );
            }
        });
    }

    $scope.process = function (csv) {
        if ($("#text-tab").hasClass("active")) {
            parseCSV(csv.data, false, csv.header).then(function(data) {showForm(data, csv.header)}, function(e) { Notification.error(e[0]) });
        } else {
            // file
            console.log($("#csv-file-input"));
            parseCSV($("#csv-file-input"), true, csv.header).then(function(data) {showForm(data, csv.header)}, function(e) { Notification.error(e[0]) });
        }
    };

    $(document).on('change', ':file', function() {
        var input = $(this).parents('.input-group').find(':text')[0];
        input.value = $(this).val().replace(/\\/g, '/').replace(/.*\//, '');
    });
});


app.controller('department', function ($scope, $rootScope, $stateParams, ngDialog, api, Notification) {
    $scope.institution = $stateParams.inst_uri;
    $scope.department  = $stateParams.dept_uri;

    $scope.openLoginForm = function() {
        ngDialog.openConfirm({template: 'tpl/login.html', data: $scope}).then(
            function(value) {
                api.doLogin($scope.user, $scope.pass, $scope.institution, $scope.department).then(
                    function(success) {
                        if (success.data == 0) {
                            $rootScope.loggedin = false;
                            Notification.error("Incorrect username or password");
                        } else if (success.data == 1) {
                            $rootScope.loggedin = true;
                            Notification.success('Logged in');
                        } else {
                            $rootScope.loggedin = false;
                            Notification.error("unknown error");
                        }
                        $scope.loginform.$setPristine();
                    },
                    function(error) {
                        Notification.error(error);
                        $scope.loginform.$setPristine();
                    }
                )
                $scope.user = "";
                $scope.pass = "";
            },
            function(value) {
                //Cancel
                $scope.user = "";
                $scope.pass = "";
            }
        );
    };

    $scope.logout = function() {
        api.doLogout().then(
            function(success) {
                $rootScope.loggedin = false;
                Notification.success("logged out");
            },
            function(error) {
                console.log($rootScope.loggedin);
                Notification.error("error logging out");
            }
        );
    };
});

app.controller('main', function($scope, $rootScope, $stateParams, ngDialog, api, Notification) {
    $scope.openLoginForm = function() {
        ngDialog.openConfirm({template: 'tpl/login.html', data: $scope}).then(
            function(value) {
                api.doLogin($scope.user, $scope.pass, null, null).then(
                    function(success) {
                        if (success.data == 0) {
                            $rootScope.loggedin = false;
                            Notification.error("Incorrect username or password");
                        } else if (success.data == 1) {
                            $rootScope.loggedin = true;
                            Notification.success('Logged in');
                        } else {
                            $rootScope.loggedin = false;
                            Notification.error("unknown error");
                        }
                    },
                    function(error) {
                        Notification.error(error);
                    }
                )
                $scope.user = "";
                $scope.pass = "";
            },
            function(value) {
                //Cancel
                $scope.user = "";
                $scope.pass = "";
            }
        );
    };

    $scope.logout = function() {
        api.doLogout().then(
            function(success) {
                $rootScope.loggedin = false;
                Notification.success("logged out");
            },
            function(error) {
                Notification.error("error logging out");
            }
        );
    };
});

app.config(function ($stateProvider, $urlRouterProvider) {
    $urlRouterProvider.otherwise("/");

    var graphTemplate = '<div style="height:100%" ng-bind-html="svg"></div>';

    $stateProvider.state('main', {
        abstract: true,
        templateUrl: 'tpl/main.html',
        controller: 'main'
    }).state('dept_list_group', {
        url: '/',
        parent: 'main',
        controller: 'dept_list_group',
        templateUrl: 'tpl/dept_list_group.html'
    }).state('dept_list', {
        url: '/:inst_uri',
        parent: 'main',
        controller: 'dept_list',
        templateUrl: 'tpl/dept_list.html'
    }).state('department.graph', {
        url: '/graph',
        abstract: true,
        template: '<div fill-screen-height class="graph" ui-view></div>'
    }).state('department.graph.all', {
        url: '/',
        controller: 'main_graph',
        template: graphTemplate
    }).state('department.graph.topic', {
        url: '/topic/:topic_id',
        controller: 'topic_graph',
        template: graphTemplate
    }).state('department.graph.unit', {
        url: '/unit/:unit_code',
        controller: 'unit_graph',
        templateUrl: 'tpl/unit_graph.html'
    }).state('department.graph.category', {
        url: '/category/:category_id',
        controller: 'category_graph',
        template: graphTemplate
    }).state('department', {
        url: '/:inst_uri/:dept_uri',
        parent: 'main',
        abstract: true,
        views: {
            'nav-menu': {
                templateUrl: 'tpl/department.html',
                controller: 'department'
            },
            '': {
                template: "<div ui-view></div>"
            }
        }
    }).state('department.units_list', {
        url: '/',
        controller: 'units',
        templateUrl: 'tpl/units_list.html'
    }).state('department.topics_list', {
        url: '/topics',
        controller: 'topics',
        templateUrl: 'tpl/topics_list.html'
    }).state('department.unit', {
        abstract: true,
        url: '/unit/:unit_code',
        controller: 'unit',
        templateUrl: 'tpl/unit.html'
    }).state('department.topic', {
        url: '/topic/:topic_id',
        controller: 'topic',
        templateUrl: 'tpl/topic.html'
    }).state('department.unit.topics', {
        url: '/',
        views: {
            'menu': {
                templateUrl: 'tpl/unit_topics_list_menu.html'
            },
            '': {
                templateUrl: 'tpl/unit_topics_list.html',
                controller: 'unit_topics'
            }
        }
    }).state('department.unit.topic_search', {
        url: '/topic_search',
        views: {
            'title': { template: '> Add topic' },
            'menu': {
                templateUrl: 'tpl/topic_search_menu.html'
            },
            '': {
                templateUrl: 'tpl/topic_search.html',
                controller: 'topic_search'
            }
        }
    }).state('department.unit.custom_topic', {
        url: '/custom_topic',
        views: {
            'title': { template: '> Add custom topic' },
            'menu': {
                templateUrl: 'tpl/custom_topic_menu.html'
            },
            '': {
                templateUrl: 'tpl/custom_topic.html',
                controller: 'custom_topic'
            }
        },
        params: {
            name: { value: "" }
        }
    }).state('department.admin', {
        url: '/admin',
        controller: 'admin',
        templateUrl: 'tpl/admin.html'
    }).state('admin', {
        // need trailing slash so it isn't matched as :inst_uri
        url: '/admin/',
        parent: 'main',
        controller: 'admin',
        templateUrl: 'tpl/admin.html'
    });
});

function enableSVGInteraction() {
    var svgElements = document.querySelector('svg');
    svgElements && svgPanZoom(svgElements, {
        panEnabled: true,
        controlIconsEnabled: true,
        zoomEnabled: true,
        dblClickZoomEnabled: true,
        mouseWheelZoomEnabled: true,
        preventMouseEventsDefault: true
    });
}

function parseCSV(csv, file, header) {
    var p1 = new Promise(function(resolve, reject) {

        if (file) {

            csv.parse({
                config: {
                    header: header,
                    skipEmptyLines: true,
                    complete: function(result, file) {
                        console.log(result);
                        if (result.errors.length > 0) {
                            reject(result.errors);
                        } else {
                            resolve(result.data);
                        }
                    }
                }
            });

        } else {

            var result = Papa.parse(csv, {
                header: header,
                skipEmptyLines: true
            });
            if (result.errors.length > 0) {
                reject(result.errors);
            } else {
                resolve(result.data);
            }
        }

    });
    return p1
}
