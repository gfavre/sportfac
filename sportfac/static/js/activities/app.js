if (!Array.prototype.indexOf){
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
if (!Array.prototype.remove){
  Array.prototype.remove = function(){
    var what, a = arguments, L = a.length, ax;
    while (L && this.length) {
        what = a[--L];
        while ((ax = this.indexOf(what)) !== -1) {
            this.splice(ax, 1);
        }
    }
    return this;
  };
}
if (!Array.prototype.map){
  Array.prototype.map = function(fun /*, thisp*/)
  {
    var len = this.length;
    if (typeof fun !== "function") {
      throw new TypeError();
    }
    var res = new Array(len);
    var thisp = arguments[1];
    for (var i = 0; i < len; i++){
      if (i in this) {
        res[i] = fun.call(thisp, this[i], i, this);
      }
    }

    return res;
  };
}
if (!Array.prototype.filter){
  Array.prototype.filter = function(fun /*, thisp*/)
  {
    var len = this.length;
    if (typeof fun !== "function"){
      throw new TypeError();
    }
    var res = [];
    var thisp = arguments[1];
    for (var i = 0; i < len; i++){
      if (i in this){
        var val = this[i]; // in case fun mutates this
        if (fun.call(thisp, val, i, this)){
          res.push(val);
        }
      }
    }
    return res;
  };
}

// Declare app level module which depends on filters, and services
angular.module('sportfacCalendar', ['sportfacCalendar.filters', 'sportfacCalendar.services',
                                    'sportfacCalendar.controllers',
                                    'ngRoute', 'ngCookies', 'ngSanitize',
                                    'ui.calendar', 'mgcrea.ngStrap']).

config(['$routeProvider', function($routeProvider) {
    'use strict';
    $routeProvider.when('/child/:childId/',
      { templateUrl: '/static/partials/activity-list.html?v=1', controller: 'ActivityCtrl' });
    $routeProvider.otherwise(
      {templateUrl: '/static/partials/activity-list.html?v=2', controller: 'ActivityCtrl'});
}]).

config(["$interpolateProvider", function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[{');
    $interpolateProvider.endSymbol('}]}');
}]);
