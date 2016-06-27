// Declare app level module which depends on filters, and services

angular.module('sportfacChildren', ['sportfacChildren.services',
                                    'sportfacChildren.controllers',
                                    'ngRoute',
                                    'ngCookies',
                                    'mgcrea.ngStrap.datepicker']).

config(['$routeProvider', function($routeProvider) {
  'use strict';
  $routeProvider.when('/edit/:childId', {templateUrl: '/static/partials/child-detail.html', controller: 'childDetailCtrl'});
  $routeProvider.when('/new', {templateUrl: '/static/partials/add-child.html', controller: 'childAddCtrl'});

  $routeProvider.otherwise({templateUrl: '/static/partials/add-child.html', controller: 'childAddCtrl'});
}]).

config(["$datepickerProvider", function($datepickerProvider) {
  angular.extend($datepickerProvider.defaults, {
    dateFormat: "dd.MM.yyyy",
    modelDateFormat: "yyyy-MM-dd",
    iconLeft: "icon-left-open",
    iconRight: "icon-right-open"
  });
}]).

config(["$interpolateProvider", function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[{');
    $interpolateProvider.endSymbol('}]}');
}]).

directive('initData', function($parse){
    return function(scope, element, attrs){
        var model = $parse(attrs.initData);
        model(scope);
        console.log('undeux');
    };
});
