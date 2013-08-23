// Declare app level module which depends on filters, and services

angular.module('sportfacChildren', ['sportfacChildren.services', 'sportfacChildren.controllers', 'ngRoute', 'ngCookies', '$strap.directives' ]).

config(['$routeProvider', function($routeProvider) {
  'use strict';
  $routeProvider.when('/edit/:childId', {templateUrl: '/static/partials/child-detail.html', controller: 'childDetailCtrl'});
  $routeProvider.when('/new', {templateUrl: '/static/partials/add-child.html', controller: 'childAddCtrl'});

  $routeProvider.otherwise({templateUrl: '/static/partials/add-child.html', controller: 'childAddCtrl'});
}]).

config(["$interpolateProvider", function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[{');
    $interpolateProvider.endSymbol('}]}');
}]).

value('$strapConfig', {
  datepicker: {
  language: 'fr',
  format: 'dd/MM/yyyy'}
});