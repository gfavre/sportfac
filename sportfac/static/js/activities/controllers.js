angular.module('sportfacCalendar.controllers', []).controller('ActivityCtrl', function($scope, $http, $store, Courses) {
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
    return $scope.selectedChild.registered.indexOf(course.id) !== -1;
  };
  $scope.isAvailable = function(course){
    return !($scope.selectedChild.school_year < course.schoolyear_min || $scope.selectedChild.school_year > course.schoolyear_max);
  };

    
  $scope.$watch('selectedChild', function(){
    var addToOthers = function(course){
      $scope.othersRegisteredEvents.push(course.toEvent("unavailable"));
    };
    var addToRegistered = function(course){
      $scope.registeredEvents.push(course.toEvent("registered"));
    };
    
    $scope.othersRegisteredEvents.length = 0;
    $scope.registeredEvents.length = 0;

    angular.forEach($scope.userChildren, function(child){
      if (child !== $scope.selectedChild) {
        angular.forEach($scope['registeredCourses_' + child.id], function(courseId){
          Courses.get(courseId).then(addToOthers);
        });
      } else {
         angular.forEach($scope['registeredCourses_' + child.id], function(courseId){
          Courses.get(courseId).then(addToRegistered);
        });
      }
    });
  });

  $scope.othersRegisteredEvents = [];
  $scope.registeredEvents = [];

  $scope.getUserChildren();
})
  .controller('ActivityListCtrl', function($scope, $http) {
  /*****************************************************************************
                    List of activities, on the left.

  *****************************************************************************/
  'use strict';
  $scope.loadActivities = function(){
      var url = '/api/activities/?year=' + $scope.selectedChild.school_year;
      $scope.activities = $http({method: 'GET', url: url, cache: true}).then(function(response){
          return response.data;
      });
  };
  $scope.$watch('selectedChild', function(){ $scope.loadActivities(); });
})
  .controller('ActivityTimelineCtrl', function($scope, $routeParams, $filter){
  /*****************************************************************************
                    Timeline

  *****************************************************************************/
  'use strict';
  // this controler is reloaded each time an activity is changed
  $scope.activityId = $routeParams.activityId;
  $scope.events = [];

  var date = new Date();
  var d = date.getDate();
  var m = date.getMonth();
  var y = date.getFullYear();
  
  $scope.$watch('othersRegisteredEvents', function(){
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });
  $scope.$watch('registeredEvents', function(){
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });

  $scope.changeActivity = function(activity){
    $scope.events.length = 0;

    for (var i=0; i<activity.courses.length; i++){
      var course = activity.courses[i];
      if ($scope.isRegistered(course)) {
        continue;
      }
      if (course.schoolyear_min > $scope.selectedChild.school_year ||
          course.schoolyear_max < $scope.selectedChild.school_year) {
        continue;
      }
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
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });

  $scope.eventSources = [$scope.registeredEvents, $scope.othersRegisteredEvents, $scope.events];
})
  .controller('ChildTimelineCtrl', function($scope, $filter, $http){
  /*****************************************************************************
                    No activity selected

  *****************************************************************************/
  'use strict';
  
  $scope.$watch('othersRegisteredEvents', function(){
    console.log('others');
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });
  $scope.$watch('registeredEvents', function(){
    console.log('self');
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });

  var date = new Date();
  var d = date.getDate();
  var m = date.getMonth();
  var y = date.getFullYear();

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
  
  
  $scope.eventSources = [$scope.registeredEvents, $scope.othersRegisteredEvents, []];
  
})
  .controller('ActivityDetailCtrl', function($scope, $routeParams){
  /*****************************************************************************
                    Detailed activity

  *****************************************************************************/

  'use strict';
  $scope.activityId = $routeParams.activityId;
  if ($scope.activityId !== undefined) {
    $scope.getDetailedActivity({'id': $scope.activityId});
  }
});