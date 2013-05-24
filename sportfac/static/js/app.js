'use strict';


// Declare app level module which depends on filters, and services
var sportfacModule = angular.module('sportfac', ['sportfac.filters', 'sportfac.services', 'sportfac.directives', 'ui.calendar']);

sportfacModule.config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/activity/:activityId/timeline', {templateUrl: '/static/partials/timeline.html', controller: 'ActivityTimelineCtrl'});
    $routeProvider.when('/activity/:activityId/detail', {templateUrl: '/static/partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
    $routeProvider.otherwise({redirectTo: '/activities'});
}]);

sportfacModule.config(function($interpolateProvider) {
  $interpolateProvider.startSymbol('{[{');
  $interpolateProvider.endSymbol('}]}');
});

var ActivityCtrl = function($scope, $http) {
  $scope.getUserChildren = function(){
    $http.get('/api/family/').success(function(data){ 
      $scope.userChildren = data; 
      $scope.selectChild(0);
    });
  };
  $scope.getDetailedActivity = function(activity){
    $http.get('/api/activities/' + activity.id).success(function(data){$scope.detailedActivity = data; });
  };
  $scope.selectChild = function(childIdx){
    if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = $scope.userChildren[childIdx];
    $scope.selectedChild.selected = true;
  };
  
  $scope.selectActivity = function(activity){
      if ($scope.selected) {
          $scope.selected.selected = false;
      }
      activity.selected = true;
      $scope.selected = activity;
      $scope.getDetailedActivity($scope.selected);
  };
  
  $scope.getUserChildren();
  $scope.detailedActivity = {};
  $scope.selected = {};
}

var ActivityListCtrl = function($scope, $http) {
  $scope.loadActivities = function(){
      var url = '/api/activities/?year=' + $scope.selectedChild.school_year;
      $scope.activities = $http.get(url).then(function(response){
          return response.data;
      });
  };
  
  
  $scope.$watch('selectedChild', function(){ $scope.loadActivities()});
};

var ActivityTimelineCtrl = function($scope, $routeParams, $filter){    
    var date = new Date();
    var d = date.getDate();
    var m = date.getMonth();
    var y = date.getFullYear();
    
    $scope.changeActivity = function(){
      $scope.events.length = 0;
      var activity = $scope.detailedActivity;
      if (activity.id) {
        for (var i=0; i<activity.courses.length; i++){
          var course = activity.courses[i];
          if (course.schoolyear_min > $scope.selectedChild.school_year || course.schoolyear_max < $scope.selectedChild.school_year) continue;
          var start = new Date(y, m, d + (course.day - date.getDay()), course.start_time.split(':')[0], course.start_time.split(':')[1]);
          var end = new Date(y, m, d + (course.day - date.getDay()), course.end_time.split(':')[0], course.end_time.split(':')[1]);
          $scope.events.push(
            {title: activity.name + ' \n ' + $filter('date')(course.start_date, 'mediumDate') +' - ' + $filter('date')(course.end_date, 'mediumDate'), 
             start: start,
             end: end,
             allDay: false}
          );
        }
      }
    };
        
    $scope.alertEventOnClick = function( date, allDay, jsEvent, view ){
        alert('clicked');
    };
    
    $scope.uiConfig = {
      calendar:{
        height: 500, aspectRatio: 4,
        //year: 2013, month: 5 - 1, date: 13,
        editable: true,
        defaultView: 'agendaWeek',
        weekends: false, allDaySlot: false,
        slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 12,
        axisFormat: 'H:mm', columnFormat: 'dddd',
        dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
        dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
        header:{left: '', center: '', right: ''},
        eventClick: $scope.alertEventOnClick,
        timeFormat: {agenda: ''}
      }
    };
    
    // 1 event source par enfant en grisé
    // 1 event source: sélection actuelle
    // 1 event source sélection déjà faite.

    $scope.events = [];
    $scope.eventSources = [$scope.events];
    $scope.$watch('detailedActivity', $scope.changeActivity);
}

var ActivityDetailCtrl = function($scope, $routeParams){
  $scope.activityId = $routeParams.activityId;
  //$scope.activityId = 3;
  if ($scope.activityId != undefined) {
    $scope.getDetailedActivity({'id': $scope.activityId});
  }
}
//ActivityDetailCtrl.$inject = ['$scope', '$routeParams'];
  
