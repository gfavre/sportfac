'use strict';


// Declare app level module which depends on filters, and services
var sportfacModule = angular.module('sportfac', ['sportfac.filters', 'sportfac.services', 'sportfac.directives', 'ui.calendar']);

sportfacModule.config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/', {templateUrl: '/static/partials/timeline.html', controller: 'ActivityTimelineCtrl'});
    $routeProvider.when('/activity/:activityId', {templateUrl: '/static/partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
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
      //$scope.getDetailedActivity($scope.selected);
      //var name = $scope.detailedActivity.name;
  };
  $scope.$watch('selected', function(){
    if ($scope.selected.id) {
        $http.get('/api/activities/' + $scope.selected.id).success(function(data){ $scope.detailedActivity = data; });
    }
  });
  $scope.detailedActivity = {}
  $scope.selected = {}
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

var ActivityTimelineCtrl = function($scope){
    var trimesters = [{'start': ''}];
    
    var date = new Date();
    var d = date.getDate();
    var m = date.getMonth();
    var y = date.getFullYear();
    
    
    $scope.events = []
    $scope.changeActivity = function(){
        $scope.events.length = 0;
    
        var activity = $scope.detailedActivity;
        if (activity.id) {
          for (var i=0; i<activity.courses.length; i++){
            var course = activity.courses[i];
            var start = new Date(y, m, d + (course.day - date.getDay()), course.start_time.split(':')[0], course.start_time.split(':')[1]);
            var end = new Date(y, m, d + (course.day - date.getDay()), course.end_time.split(':')[0], course.end_time.split(':')[1]);
            $scope.events.push(
              {title: activity.name, 
               start: start,
               end: end,
               allDay: false}
            );
          }
        }
    };
    $scope.$watch('detailedActivity', $scope.changeActivity);

        
    $scope.alertEventOnClick = function( date, allDay, jsEvent, view ){
        $scope.events.push({title: 'test',
                            start: new Date(y, m, d, 15, 0), 
                            end: new Date(y, m, d, 16, 0),
                            allDay: false });
    };
    
    $scope.uiConfig = {
      calendar:{
        height: 500, aspectRatio: 4,
        //year: 2013, month: 5 - 1, date: 13,
        editable: true,
        defaultView: 'agendaWeek',
        weekends: false, allDaySlot: false,
        slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 12,
        axisFormat: 'H:mm', columnFormat: 'dddd d MMM yyyy',
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
  
