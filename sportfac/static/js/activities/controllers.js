angular.module('sportfacCalendar.controllers', [])
  
.controller('ChildrenCtrl', function($scope, $http, $store, Courses, ModelUtils, $window) {
  'use strict';
  $scope.toSave = undefined;
  
  $scope.getUserChildren = function(){
    $http.get('/api/family/').success(function(data){
      $scope.userChildren = data;
      angular.forEach($scope.userChildren, function(child){
        $store.bind($scope, 'registeredCourses_' + child.id);
        child.registered = $scope['registeredCourses_' + child.id];
      });
    });   
  };
  
  $scope.selectChild = function(childId){
    angular.forEach($scope.userChildren, function(child){
      if (child.id === childId){ 
        child.selected = true;
        $scope.selectedChild = child; 
      } else {
        child.selected = false;
      }
    });
    $scope.loadActivities();
    $scope.selectedActivity = {};
  };
  
  $scope.selectActivity = function(activity){
    if ($scope.selectedActivity) {
        $scope.selectedActivity.selected = false;
    }
    activity.selected = true;
    $scope.selectedActivity = activity;
  };

  
  $scope.loadActivities = function(){
    var url = '/api/activities/?year=' + $scope.selectedChild.school_year;
    $scope.activities = $http({method: 'GET', url: url, cache: true}).then(function(response){
        return response.data;
    });
  };
  
})


/*******************************************************************************
        Activities management, i.e. a child tab in activities application
*******************************************************************************/
.controller('ActivityCtrl', function($scope, $http, $store, $routeParams, Courses, ModelUtils, $window) {
 var childId = parseInt($routeParams.childId);
 
 $scope.$watch('userChildren', function(){
   if (!angular.isDefined($scope.userChildren)) return;

   if (angular.isDefined(childId)){
       $scope.selectChild(childId);
   } else{
       $scope.selectChild($scope.userChildren[0].id);
   }
   
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
  
  $scope.isRegistered = function(course){
    return $scope.selectedChild.registered.indexOf(course.id) !== -1;
  };
  $scope.isAvailable = function(course){
    return !($scope.selectedChild.school_year < course.schoolyear_min || $scope.selectedChild.school_year > course.schoolyear_max);
  };

    
    
  $scope.registerCourses = function(){
    $scope.toSave = $scope.othersRegisteredEvents.length + $scope.registeredEvents.length;
    angular.forEach($scope.userChildren, function(child){
      angular.forEach(child.registered, function(courseId){
        var registration = {child: child.id, course: courseId};
        ModelUtils.save('/api/registrations/', registration, $scope.errors).then(function(){
          $scope.toSave -= 1;
          // change status          
        });
      });
    });
  };
  
  $scope.$watch('toSave', function(newValue, oldValue){
    if (newValue === 0){
      console.log('evt triggered');
      $window.location.href = '/activities/confirm'; 
    }});
  
  $scope.othersRegisteredEvents = [];
  $scope.registeredEvents = [];
  $scope.getUserChildren();
})

/*******************************************************************************
                    List of activities, on the left.
*******************************************************************************/
.controller('ActivityListCtrl', function($scope, $http) {
  'use strict';
})

/*******************************************************************************
                    Timeline

*******************************************************************************/
.controller('ActivityTimelineCtrl', function($scope, $routeParams, $filter){
  'use strict';
  var today = new Date();
  var year = today.getFullYear();
  var month = today.getMonth();
  var day = today.getDate();
  // this controler is reloaded each time an activity is changed
  $scope.events = [];
    
  $scope.$watch('selectedActivity', function(){
    if (!angular.isDefined($scope.selectedActivity)){
        return;
    }
    $scope.changeActivity($scope.selectedActivity);
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });

  

    
  $scope.$watch('othersRegisteredEvents', function(){
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });
  $scope.$watch('registeredEvents', function(){
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });

  $scope.changeActivity = function(activity){
    if (!angular.isDefined(activity.courses)){
        return;
    }
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
      var start = new Date(year, month, day + (course.day - today.getDay()), course.start_time.split(':')[0], course.start_time.split(':')[1]);
      var end = new Date(year, month, day + (course.day - today.getDay()), course.end_time.split(':')[0], course.end_time.split(':')[1]);

      $scope.events.push({
         title: activity.name,
         start: start,
         end: end,
         //start_text: 'adadsas' + day + (course.day - day),
         //end_text: day +  course.day - day,
         allDay: false,
         className: $scope.isRegistered(course) ? "registered": "available" ,
         course: course,
         activityId: activity.id
      });
    };
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
      year: year, month: month, date: day,
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
  
  
  

  $scope.eventSources = [$scope.registeredEvents, $scope.othersRegisteredEvents, $scope.events];
})
  .controller('ChildTimelineCtrl', function($scope, $filter, $http){
  /*****************************************************************************
                    No activity selected

  *****************************************************************************/
  'use strict';
  
  $scope.$watch('othersRegisteredEvents', function(){
    $scope.weekagenda.fullCalendar('render');
    $scope.weekagenda.fullCalendar('refetchEvents');
  });
  $scope.$watch('registeredEvents', function(){
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