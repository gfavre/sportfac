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

// Declare app level module which depends on filters, and services
var sportfacModule = angular.module('sportfac', ['sportfac.services', 'ui.calendar']);

sportfacModule.config(['$routeProvider', function($routeProvider) {
  'use strict';
  $routeProvider.when('/activity/:activityId/timeline', 
      {templateUrl: '/static/partials/timeline.html', controller: 'ActivityTimelineCtrl'});
    
  $routeProvider.when('/activity/:activityId/detail', 
      {templateUrl: '/static/partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
    
  $routeProvider.otherwise({templateUrl: '/static/partials/timeline.html', controller: 'ChildTimelineCtrl'});
}]).config(function($interpolateProvider) {
  $interpolateProvider.startSymbol('{[{');
  $interpolateProvider.endSymbol('}]}');
});


var ActivityCtrl = function($scope, $http, $store) {
  'use strict';
  $scope.getUserChildren = function(){
    $http.get('/api/family/').success(function(data){ 
      $scope.userChildren = data;
      for (var i=0; i<data.length; i++){
        $store.bind($scope, 'registeredCourses_' + data[i].id);
      }
      $scope.selectChild(0);
    });
  };
  
  $scope.selectChild = function(childIdx){
    if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = $scope.userChildren[childIdx];
    $scope.selectedChild.selected = true;
    $scope.selectedChild.registered = $scope['registeredCourses_' + $scope.selectedChild.id];
  };
  
  $scope.getDetailedActivity = function(activity_id, callback){
    var url = '/api/activities/' + activity_id;
    $http({url: url, method: 'GET', cache: true }).success(function(data){
      callback(data); 
    });
  };
  
  $scope.selectActivity = function(activity){
      if ($scope.selectedActivity) {
          $scope.selectedActivity.selected = false;
      }
      activity.selected = true;
      $scope.selectedActivity = activity;
  };
  
  $scope.isRegistered = function(course){
    return $scope.selectedChild.registered.indexOf(course.id) != -1;
  };
  $scope.isAvailable = function(course){
    return !($scope.selectedChild.school_year < course.schoolyear_min || $scope.selectedChild.school_year > course.schoolyear_max);
  };
  
  $scope.$watch('selectedChild', function(){
    $scope.othersRegisteredEvents.length = 0;
    angular.forEach($scope.userChildren, function(child){
      if (child != $scope.selectedChild) {
        $scope.othersRegisteredEvents.push.apply($scope.othersRegisteredEvents, $scope['registeredCourses_' + child.id]);
      }
    });
  });
  
  $scope.othersRegisteredEvents = [];
  $scope.getUserChildren();  
};



var ActivityListCtrl = function($scope, $http) {
  'use strict';
  $scope.loadActivities = function(){
      var url = '/api/activities/?year=' + $scope.selectedChild.school_year;
      $scope.activities = $http({method: 'GET', url: url, cache: true}).then(function(response){
          return response.data;
      });
  };
  $scope.$watch('selectedChild', function(){ $scope.loadActivities(); });
};


var ActivityTimelineCtrl = function($scope, $routeParams, $filter, $http){
    'use strict';  
    // this controler is reloaded each time an activity is changed
    $scope.activityId = $routeParams.activityId;
    $scope.events = [];
    $scope.registeredEvents = [];
    $scope.othersEvents = [];
    
    var date = new Date();
    var d = date.getDate();
    var m = date.getMonth();
    var y = date.getFullYear();
    
    $scope.getCourse = function(courseId, callback){
      var url = '/api/courses/' + courseId;
      $http({url: url, method: 'GET', cache: true }).success(function(data){
        callback(data); 
      });
    };

    $scope.getStartDate = function(course){
        return new Date(y, m, d + (course.day - date.getDay()), 
                        course.start_time.split(':')[0], 
                        course.start_time.split(':')[1]);
    };
    $scope.getEndDate = function(course){
        return new Date(y, m, d + (course.day - date.getDay()), 
                        course.end_time.split(':')[0], 
                        course.end_time.split(':')[1]);
    };
    
    $scope.convertCourse = function(course, css){
        return {title: course.activity.name, 
                start: $scope.getStartDate(course), end: $scope.getEndDate(course),
                start_text: d, end_text: d, allDay: false,
                className: css, course: course, activityId: course.activity.id};
    };
    
    $scope.reloadRegisteredEvents = function(){
      var addToRegistered = function(course){
        $scope.registeredEvents.push($scope.convertCourse(course, "registered"));
        $scope.weekagenda.fullCalendar('render');
        $scope.weekagenda.fullCalendar('refetchEvents');

      };
      $scope.registeredEvents.length = 0;
      for (var i=0; i<$scope.selectedChild.registered.length; i++) {
        $scope.getCourse($scope.selectedChild.registered[i], addToRegistered);
      }
    };
    
    $scope.reloadOthersEvents = function(){
      var addToRegistered = function(course){
        $scope.registeredEvents.push($scope.convertCourse(course, "unavailable"));
        $scope.weekagenda.fullCalendar('render');
        $scope.weekagenda.fullCalendar('refetchEvents');
      };
      $scope.othersEvents.length = 0;
      for (var i=0; i<$scope.othersRegisteredEvents.length; i++) {
        $scope.getCourse($scope.othersRegisteredEvents[i], addToRegistered);
      }
    };
    
    $scope.changeActivity = function(activity){
      $scope.events.length = 0;
      
      for (var i=0; i<activity.courses.length; i++){
        var course = activity.courses[i];
        if ($scope.isRegistered(course)) continue;
        if (course.schoolyear_min > $scope.selectedChild.school_year || course.schoolyear_max < $scope.selectedChild.school_year) { continue; }
        var start = new Date(y, m, d + (course.day - date.getDay()), course.start_time.split(':')[0], course.start_time.split(':')[1]);
        var end = new Date(y, m, d + (course.day - date.getDay()), course.end_time.split(':')[0], course.end_time.split(':')[1]);
        
        $scope.events.push({
           title: activity.name, 
           start: start,
           end: end,
           start_text: d + (course.day - date.getDay()),
           end_text: d+  course.day - date.getDay(),
           allDay: false,
           className: $scope.isRegistered(course) ? "registered": "available" ,
           course: course,
           activityId: activity.id
        });
      }
    };
    
    $scope.eventClick = function( calEvent, jsEvent, view ){
      $scope.$apply(function(){
        if (!$scope.isAvailable(calEvent.course)){
          return;
        }
        var courseId = calEvent.course.id;
        var index = $scope.selectedChild.registered.indexOf(courseId);
        if (index === -1){
          // unregistered event, register it
          calEvent.className = 'registered';
          $scope.selectedChild.registered.push(courseId);
        } else {
          // registered event, unregister it
          calEvent.className = 'available';
          $scope.selectedChild.registered.splice(index, 1);
          if (calEvent.activityId !== $scope.activityId){
              $scope.weekagenda.fullCalendar('removeEvents', calEvent._id);
          } else{
              $scope.weekagenda.fullCalendar('updateEvent', calEvent);
          }
        }
        $scope.weekagenda.fullCalendar('rerenderEvents');
      }); 
    };
    
    $scope.uiConfig = {
      calendar:{
        height: 450, aspectRatio: 2,
        year: y, month: m, date: d,
        editable: false,
        defaultView: 'agendaWeek', weekends: false, allDaySlot: false,
        slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 13,
        axisFormat: 'H:mm', columnFormat: 'dddd', header:{left: '', center: '', right: ''},
        dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'], 
        dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
        timeFormat: {agenda: 'd'}, lazyFetching: true,
        eventClick: $scope.eventClick,
        eventAfterRender: function(event, element, view){
          var text = $filter('date')(event.course.start_date, 'shortDate') +' - ' + $filter('date')(event.course.end_date, 'shortDate');
          $('.fc-event-time', element).text(text);
        }
      }
    };

    $scope.getDetailedActivity($scope.activityId, function(detailedActivity){
      $scope.detailedActivity = detailedActivity;
      $scope.changeActivity(detailedActivity);
      $scope.reloadRegisteredEvents();
      $scope.reloadOthersEvents();
      $scope.weekagenda.fullCalendar('render');
      $scope.weekagenda.fullCalendar('refetchEvents');
    });

    $scope.eventSources = [$scope.registeredEvents, $scope.events];
};

var ChildTimelineCtrl = function($scope, $filter, $http){
    'use strict';  
    // this controler is reloaded each time an activity is changed
    $scope.registeredEvents = [];
    $scope.othersEvents = [];
    $scope.eventSources = [$scope.registeredEvents, $scope.othersEvents];
    
    var date = new Date();
    var d = date.getDate();
    var m = date.getMonth();
    var y = date.getFullYear();
    
    $scope.getCourse = function(courseId, callback){
      var url = '/api/courses/' + courseId;
      $http({url: url, method: 'GET', cache: true }).success(function(data){
        callback(data); 
      });
    };

    $scope.getStartDate = function(course){
        return new Date(y, m, d + (course.day - date.getDay()), 
                        course.start_time.split(':')[0], 
                        course.start_time.split(':')[1]);
    };
    $scope.getEndDate = function(course){
        return new Date(y, m, d + (course.day - date.getDay()), 
                        course.end_time.split(':')[0], 
                        course.end_time.split(':')[1]);
    };
    
    $scope.convertCourse = function(course, css){
        return {title: course.activity.name, 
                start: $scope.getStartDate(course), end: $scope.getEndDate(course),
                start_text: d, end_text: d, allDay: false,
                className: css, course: course, activityId: course.activity.id};
    };
    
    $scope.reloadRegisteredEvents = function(){
      var addToRegistered = function(course){
        $scope.registeredEvents.push($scope.convertCourse(course, "registered"));
        $scope.weekagenda.fullCalendar('render');
        $scope.weekagenda.fullCalendar('refetchEvents');

      };
      $scope.registeredEvents.length = 0;
      for (var i=0; i<$scope.selectedChild.registered.length; i++) {
        $scope.getCourse($scope.selectedChild.registered[i], addToRegistered);
      }
    };
    
    $scope.reloadOthersEvents = function(){
      var addToRegistered = function(course){
        $scope.registeredEvents.push($scope.convertCourse(course, "unavailable"));
        $scope.weekagenda.fullCalendar('render');
        $scope.weekagenda.fullCalendar('refetchEvents');
      };
      $scope.othersEvents.length = 0;
      for (var i=0; i<$scope.othersRegisteredEvents.length; i++) {
        $scope.getCourse($scope.othersRegisteredEvents[i], addToRegistered);
      }
    };
    
    
    $scope.eventClick = function( calEvent, jsEvent, view ){
      $scope.$apply(function(){
        if (!$scope.isAvailable(calEvent.course)){
          return;
        }
        var courseId = calEvent.course.id;
        var index = $scope.selectedChild.registered.indexOf(courseId);
        if (index === -1){
          // unregistered event, register it
          calEvent.className = 'registered';
          $scope.selectedChild.registered.push(courseId);
        } else {
          // registered event, unregister it
          calEvent.className = 'available';
          $scope.selectedChild.registered.splice(index, 1);
          if (calEvent.activityId !== $scope.activityId){
              $scope.weekagenda.fullCalendar('removeEvents', calEvent._id);
          } else{
              $scope.weekagenda.fullCalendar('updateEvent', calEvent);
          }
        }
        $scope.weekagenda.fullCalendar('rerenderEvents');
      }); 
    };
    
    $scope.uiConfig = {
      calendar:{
        height: 450, aspectRatio: 2,
        year: y, month: m, date: d,
        editable: false,
        defaultView: 'agendaWeek', weekends: false, allDaySlot: false,
        slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 13,
        axisFormat: 'H:mm', columnFormat: 'dddd', header:{left: '', center: '', right: ''},
        dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'], 
        dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
        timeFormat: {agenda: 'd'}, lazyFetching: true,
        eventClick: $scope.eventClick,
        eventAfterRender: function(event, element, view){
          var text = $filter('date')(event.course.start_date, 'shortDate') +' - ' + $filter('date')(event.course.end_date, 'shortDate');
          $('.fc-event-time', element).text(text);
        }
      }
    };
    
    
    
    $scope.reloadRegisteredEvents();
    $scope.reloadOthersEvents();
};




var ActivityDetailCtrl = function($scope, $routeParams){
  'use strict';
  $scope.activityId = $routeParams.activityId;
  if ($scope.activityId !== undefined) {
    $scope.getDetailedActivity({'id': $scope.activityId});
  }
};