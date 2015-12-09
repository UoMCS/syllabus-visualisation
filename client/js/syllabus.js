let app = angular.module('syllabus', ['ui.router', 'ui.bootstrap', 'ui-notification', 'ngTagsInput']);

app.config(function(NotificationProvider) {
    NotificationProvider.setOptions({
        positionX: 'left',
        positionY: 'bottom'
    });
});

app.factory('wp', ($http, api) =>
    ({
        suggestions: search => $http.jsonp('//en.wikipedia.org/w/api.php', {
                params: {
                    callback: 'JSON_CALLBACK', // So that JSONP works correctly
                    action: 'opensearch',
                    format: 'json',
                    search: search
                }
            }).then(response => response.data[1])
        ,
        search: search => $http.jsonp('//en.wikipedia.org/w/api.php', {
                params: {
                    callback: 'JSON_CALLBACK', // So that JSONP works correctly
                    format: 'json',
                    action: 'query',
                    list: 'search',
                    srsearch: search,
                    srprop: 'redirecttitle|sectiontitle'
                }
            })
        ,
        additionalInfo: searchResult => {
            let titles = searchResult.pages.map(page => page.title);
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
            }).then(response => {
                // Re-map by title
                let pageInfo = {};
                response.data.query.pageids.forEach(pageId => {
                    let p = response.data.query.pages[pageId];
                    pageInfo[p.title] = p;
                });

                // Attach additional data to results
                searchResult.pages.forEach(function(page) {
                    page.extract = pageInfo[page.title].extract;

                    // Mark disambiguation pages
                    page.isDisambiguation = pageInfo[page.title].categories.some(
                            category => (category.title === "Category:All disambiguation pages")
                    );
                });

                // Filter out disambiguation pages
                let filteredPages = searchResult.pages.filter(page => !page.isDisambiguation);

                searchResult.numDisambiguationPages = searchResult.pages.length - filteredPages.length;
                searchResult.pages = filteredPages;

                // Fetch additional info from our API
                api.additionalInfo(searchResult);
            });
        }
    })
);

app.factory('api', ($http, $stateParams, $sce) => // FIXME: don't use stateParams here
    ({
        additionalInfo: searchResult => {
            let titles = searchResult.pages.map(page => page.title);
            return $http.get('api/unit_topics', {
                params: {
                    topic_name: titles.join('|'),
                    embed: 'topic,unit'
                }
            }).then(response => {
                let units = new Map(); // Gather units for topics

                response.data.unit_topics.forEach(unit_topic => {
                    const topic = unit_topic.topic,
                          unit = unit_topic.unit;

                    // Make sure topic is already in the map
                    if (!units.has(topic.name)) units.set(topic.name,[]);

                    units.get(topic.name).push(unit.code);
                });

                searchResult.pages.forEach(page => {
                    if (units.has(page.title)) {
                        page.units = units.get(page.title);
                        // TODO: remove unit_code from units
                        page.isAdded = (page.units.indexOf($stateParams.unit_code) !== -1);
                    } else {
                        page.isAdded = false;
                    }
                });

                console.log(searchResult.pages);
            });
        },

        addUnitTopic: (unitCode, topicName) =>
            $http.post('api/unit_topics/add', {
                unit_code: unitCode,
                topic_name: topicName
            }),

        addCustomUnitTopic: (unitCode, topicName, topicDescr, topicKeywords) =>
            $http.post('api/unit_topics/add', {
                unit_code: unitCode,
                topic_name: topicName,
                topic_description: topicDescr,
                topic_keywords: topicKeywords
            }),

        updateUnitTopic: unitTopic =>
            $http.post('api/unit_topics/update', unitTopic),

        removeUnitTopic: id =>
            $http.post('api/unit_topics/remove', {
                unit_topic_id: id
            }),

        fetchUnit: unitCode => $http.get(`api/unit/${unitCode}`),

        fetchUnitTopics: unitCode =>
            $http.get('api/unit_topics', {
                params: {
                    unit_code: unitCode,
                    embed: 'topic,contexts'
                }
            }).then(response => {
                return response.data.unit_topics;
            }),

        fetchGraph: url =>
            $http.get(url).then(response => {
                let data = response.data;
                data += "<script>enableSVGInteraction()</script>"; // FIXME: hacky
                return $sce.trustAsHtml(data);
            })
    })
);

app.controller('units', ($scope, $http) => {
    $http.get('api/units')
        .success(data => { $scope.units = data.units; });
});

app.controller('unit', (api, $scope, $http, $stateParams) => {
    let unitCode = $stateParams.unit_code;

    api.fetchUnit(unitCode).success(data => {
        $scope.unit = data.unit;
        $scope.unitLoaded = true;
    });
});

app.controller('unit_topics', ($scope, $http, $stateParams, Notification, api) => {
    let unitCode = $stateParams.unit_code;

    api.fetchUnitTopics(unitCode).then(unitTopics => {
        $scope.unit_topics = unitTopics;
        let topics = unitTopics.map(item => item.topic);
        $scope.context_search = query => {
            // Return topics which start with query
            let regExp = new RegExp('^' + query, 'i');
            return topics.filter(topic => regExp.test(topic.name));
        };
        $scope.contentLoaded = true;
    });

    $scope.edit = unitTopic => {
        unitTopic.isEditing = true;
    };

    $scope.remove = unitTopic => {
        api.removeUnitTopic(unitTopic.id).then(() => {
            Notification.success('Topic removed');
            // Re-fetch the list of topics
            // TODO: could just remove unitTopic from $scope.unit_topics?
            api.fetchUnitTopics(unitCode).then(unitTopics => {
                $scope.unit_topics = unitTopics;
            });
        });
    };

    $scope.save = unitTopic => {
        api.updateUnitTopic(unitTopic).then(() => {
            unitTopic.isEditing = false;
            Notification.success('Topic saved');
        });
    };

    $scope.cancel = unitTopic => {
        unitTopic.isEditing = false;
    };
});

app.controller('custom_topic', ($scope, $stateParams, $state, api, Notification) => {

    $scope.addTopic = () => {
        api.addCustomUnitTopic($scope.unit.code, $scope.name, $scope.description, $scope.keywords).then(() => {
            $state.go('unit.topics');
            Notification.success('Topic added');
        });
    };
});

app.controller('topic_search', ($scope, wp, api, Notification) => {
    $scope.wpSuggestions = wp.suggestions;

    $scope.wpSearch = () => {
        wp.search($scope.query).then(response => {
            $scope.searchResult = {pages: response.data.query.search};

            // Fetch additional info
            wp.additionalInfo($scope.searchResult);
        });
    };

    $scope.addTopic = (topicName) => {
        api.addUnitTopic($scope.unit.code, topicName).then(() => {
            Notification.success('Topic added');
            api.additionalInfo($scope.searchResult);
        });
    };
});

// Makes the element fill the rest of the screen
app.directive('fillScreenHeight', () => ({
      link: (scope, element, _) => {
          $(window).resize(() => {
              element.height($(window).height() - element.offset().top);
              // TODO: reset svg-pan-zoom
          });
          $(window).resize(); // Trigger initial resize
      }
  })
);

app.controller('main_graph', ($scope, api) => {
    api.fetchGraph('api/graph').then(svg => {
        $scope.svg = svg;
    });
});

app.controller('unit_graph', ($scope, $stateParams, api) => {
    let unitCode = $stateParams.unit_code;

    $scope.unitCode = unitCode;

    api.fetchGraph(`api/graph/unit/${unitCode}`).then(svg => {
        $scope.svg = svg;
    });
});

app.controller('topic_graph', ($scope, $stateParams, api) => {
    let topicId = $stateParams.topic_id;

    api.fetchGraph(`api/graph/topic/${topicId}`).then(svg => {
        $scope.svg = svg;
    });
});

app.controller('category_graph', ($scope, $stateParams, api) => {
    let categoryId = $stateParams.category_id;

    api.fetchGraph(`api/graph/category/${categoryId}`).then(svg => {
        $scope.svg = svg;
    });
});

app.config(($stateProvider, $urlRouterProvider) => {
    $urlRouterProvider.otherwise("/");

    let graphTemplate = '<div style="height:100%" ng-bind-html="svg"></div>';

    $stateProvider
        .state('main', {
            abstract: true,
            templateUrl: 'tpl/main.html'
        })
        .state('graph', {
            parent: 'main',
            url: '/graph',
            abstract: true,
            template: '<div fill-screen-height class="graph" ui-view></div>'
        })
        .state('graph.all', {
            url: '/',
            controller: 'main_graph',
            template: graphTemplate
        })
        .state('graph.topic', {
            url: '/topic/:topic_id',
            controller: 'topic_graph',
            template: graphTemplate
        })
        .state('graph.unit', {
            url: '/unit/:unit_code',
            controller: 'unit_graph',
            templateUrl:'tpl/unit_graph.html'
        })
        .state('graph.category', {
            url: '/category/:category_id',
            controller: 'category_graph',
            template: graphTemplate
        })
        .state('units_list', {
            url: '/',
            parent: 'main',
            controller: 'units',
            templateUrl:'tpl/units_list.html'
        })
        .state('unit', {
            abstract: true,
            parent: 'main',
            url: '/unit/:unit_code',
            controller: 'unit',
            templateUrl: 'tpl/unit.html'
        })
        .state('unit.topics', {
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
        })
        .state('unit.topic_search', {
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
        })
        .state('unit.custom_topic', {
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
        });
});

function enableSVGInteraction() {
    let svgElements = document.querySelector('svg');
    svgElements && svgPanZoom(svgElements);
}