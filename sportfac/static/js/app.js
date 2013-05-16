'use strict';


// Declare app level module which depends on filters, and services
var sportfacModule = angular.module('sportfac', ['sportfac.filters', 'sportfac.services', 'sportfac.directives', 'ui.calendar']);

sportfacModule.config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/', {templateUrl: '/static/partials/activity-list.html', controller: 'ActivityListCtrl'});
    $routeProvider.when('/activity/:activityId', {templateUrl: '/static/partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
    $routeProvider.when('/timeline/:activityId', {templateUrl: '/static/partials/timeline.html', controller: 'ActivityTimelineCtrl'});
    $routeProvider.otherwise({redirectTo: '/activities'});
}]);

sportfacModule.config(function($interpolateProvider) {
  $interpolateProvider.startSymbol('{[{');
  $interpolateProvider.endSymbol('}]}');
});

var ActivityCtrl = function($scope, $http) {
  $scope.getDetailedActivity = function(activity){
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
    
}

var ActivityListCtrl = function($scope, $http) {  
  $scope.loadActivities = function(){
      $scope.activities = $http.get('/api/activities/').then(function(response){
          return response.data;
      });
  };
  $scope.orderProp = 'name';
  $scope.loadActivities();
  
}

var ActivityTimelineCtrl = function($scope, $routeParams){
    $scope.activityId = $routeParams.activityId;
    //$scope.activityId = 3;
    if ($scope.activityId != undefined) {
        $scope.getDetailedActivity({'id': $scope.activityId});
    }
    var trimesters = [{'start': ''}];
    
    var date = new Date();
    var d = date.getDate();
    var m = date.getMonth();
    var y = date.getFullYear();
    $scope.events = [
      {title: 'All Day Event',start: new Date(y, m, 1)},
      {title: 'Long Event',start: new Date(y, m, d - 5),end: new Date(y, m, d - 2)},
      {id: 999,title: 'Repeating Event',start: new Date(y, m, d - 3, 16, 0),allDay: false},
      {id: 999,title: 'Repeating Event',start: new Date(y, m, d + 4, 16, 0),allDay: false},
      {title: 'Birthday Party',start: new Date(y, m, d + 1, 19, 0),end: new Date(y, m, d + 1, 22, 30),allDay: false},
      
      {title: 'Birthday Party',start: new Date(y, m, d + 1, 19, 0),end: new Date(y, m, d + 1, 22, 30),allDay: false},
      
    ];
    
    $scope.alertEventOnClick = function( date, allDay, jsEvent, view ){
        $scope.$apply(function(){
          alert('Day Clicked ' + date);
        });
    };
    
    $scope.uiConfig = {
      calendar:{
        height: 500, aspectRatio: 4,
        //year: 2013, month: 9, date: 15,
        editable: false,
        defaultView: 'agendaWeek',
        weekends: false, allDaySlot: false,
        slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 12,
        axisFormat: 'H:mm', columnFormat: 'dddd',
        dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
        dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
        header:{
          left: '',
          center: '',
          right: ''
        },
        
        eventClick: $scope.alertEventOnClick,
      }
    };
    
    // 1 event source par enfant en grisé
    // 1 event source: sélection actuelle
    // 1 event source sélection déjà faite.
    $scope.eventSources = [$scope.events];
}

var ActivityDetailCtrl = function($scope, $routeParams){
  $scope.activityId = $routeParams.activityId;
  //$scope.activityId = 3;
  if ($scope.activityId != undefined) {
    $scope.getDetailedActivity({'id': $scope.activityId});
  }
}
//ActivityDetailCtrl.$inject = ['$scope', '$routeParams'];
  
