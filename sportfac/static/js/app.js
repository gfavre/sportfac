'use strict';


// Declare app level module which depends on filters, and services
var sportfacModule = angular.module('sportfac', ['sportfac.filters', 'sportfac.services', 'sportfac.directives']);

sportfacModule.config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/', {templateUrl: '/static/partials/activity-list.html', controller: 'ActivityListCtrl'});
    $routeProvider.when('/activity/:activityId', {templateUrl: '/static/partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
    $routeProvider.otherwise({redirectTo: '/activities'});
}]);

sportfacModule.config(function($interpolateProvider) {
  $interpolateProvider.startSymbol('{[{');
  $interpolateProvider.endSymbol('}]}');
});


var ActivityListCtrl = function($scope, $http) {
  
  $scope.loadActivities = function(){
      $scope.activities = $http.get('/api/activities/').then(function(response){
          return response.data;
      });
  };
  
  $scope.showDetails = function(activity){
      $scope.detailedActivity = $http.get('/api/activities/' + activity.id).then(function(response){
         return response.data 
      });
  };
  
  $scope.selectActivity = function(activity){
      if ($scope.selected) {
          $scope.selected.selected = false;
      }
      activity.selected = true;
      $scope.selected = activity;
  };
  
  $scope.detailedActivity = {};
  $scope.orderProp = 'name';
  $scope.loadActivities();
  
}

var ActivityDetailCtrl = function($scope, $routeParams){
  $scope.activityId = $routeParams.activityId;
}
//ActivityDetailCtrl.$inject = ['$scope', '$routeParams'];
  
