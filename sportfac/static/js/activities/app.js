if (!Array.prototype.indexOf) {
  Array.prototype.indexOf = function (obj, fromIndex) {
    if (fromIndex === null) {
        fromIndex = 0;
    } else if (fromIndex < 0) {
        fromIndex = Math.max(0, this.length + fromIndex);
    }
    for (var i = fromIndex, j = this.length; i < j; i++) {
        if (this[i] === obj) { return i; }
    }
    return -1;
  };
}

Array.prototype.remove = function() {
    var what, a = arguments, L = a.length, ax;
    while (L && this.length) {
        what = a[--L];
        while ((ax = this.indexOf(what)) !== -1) {
            this.splice(ax, 1);
        }
    }
    return this;
};




// Declare app level module which depends on filters, and services
angular.module('sportfacCalendar', ['sportfacCalendar.services', 'sportfacCalendar.controllers', 'ngCookies', 'ui.calendar', '$strap.directives']).
  config(['$routeProvider', function($routeProvider) {
    'use strict';
    $routeProvider.when('/child/:childId/',
      { templateUrl: '/static/partials/activity-list.html', controller: 'ActivityCtrl' });
    $routeProvider.otherwise(
      {templateUrl: '/static/partials/activity-list.html', controller: 'ActivityCtrl'});
    /*
    
    $routeProvider.when('/activity/:activityId/timeline',
      {templateUrl: '/static/partials/timeline.html', controller: 'ActivityTimelineCtrl'});
    $routeProvider.when('/activity/:activityId/detail',
      {templateUrl: '/static/partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
    $routeProvider.otherwise({templateUrl: '/static/partials/timeline.html', controller: 'ChildTimelineCtrl'});*/
}]).
  config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[{');
    $interpolateProvider.endSymbol('}]}');
});