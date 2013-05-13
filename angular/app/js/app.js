'use strict';


// Declare app level module which depends on filters, and services
angular.module('sportfac', ['sportfac.filters', 'sportfac.services', 'sportfac.directives']).
  config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/activities', {templateUrl: 'partials/activity-list.html', controller: 'ActivityListCtrl'});
    $routeProvider.when('/activity/:activityId', {templateUrl: 'partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
    $routeProvider.otherwise({redirectTo: '/activities'});
  }]);

var ActivityListCtrl = function($scope, $http) {
  $http.get('activities.json').success(function(data){
     $scope.activities = data 
  });
  $scope.orderProp = 'title';
}

var ActivityDetailCtrl = function($scope, $routeParams){
  $scope.activityId = $routeParams.activityId;  
}
//ActivityDetailCtrl.$inject = ['$scope', '$routeParams'];
  
