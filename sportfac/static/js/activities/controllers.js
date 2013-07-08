angular.module('sportfacCalendar.controllers', [])
  
.controller('ChildrenCtrl', function($scope, $store, $routeParams, ChildrenService, $window) {
  'use strict';
  $scope.toSave = undefined;
  
  ChildrenService.all().then(function(children){
    console.log('childrenctrl init');
    $scope.userChildren = children;
    angular.forEach($scope.userChildren, function(child){
      $store.bind($scope, 'registeredCourses_' + child.id);
      child.registered = $scope['registeredCourses_' + child.id];
    });
    
    var childId = parseInt($routeParams.childId, 10);
    if (isNaN(childId)) $window.location.href = './#/child/' + $scope.userChildren[0].id + '/';
    $scope.selectChild(childId);
  });
  
  $scope.selectChild = function(childId){
    angular.forEach($scope.userChildren, function(child){
      if (child.id === childId){ 
        child.selected = true;
        $scope.selectedChild = child;
      } else {
        child.selected = false;
      }
    });
    
  };
})


/*******************************************************************************
        Activities management, i.e. a child tab in activities application
*******************************************************************************/
.controller('ActivityCtrl', function($scope, $http, $store, $routeParams, CoursesService, ModelUtils, $window) { 
  console.log('init activity');
  $scope.$watch('selectedChild', function(newval, oldval){
    if (angular.isDefined(newval) ){
      $scope.loadActivities();
      $scope.selectedActivity = {};
      $scope.updateOthersEvents();
    }
  });
  
  $scope.selectActivity = function(activity){
    if ($scope.selectedActivity) $scope.selectedActivity.selected = false;
    activity.selected = true;
    $scope.selectedActivity = activity;
  };
  
  $scope.loadActivities = function(){
    var url = '/api/activities/?year=' + $scope.selectedChild.school_year;
    $scope.activities = $http({method: 'GET', url: url, cache: true}).then(function(response){
        return response.data;
    });
  };
  
  $scope.$watch('selectedChild.registered.length', function(newvalue, oldvalue){
    if (angular.isDefined(newvalue)){
      console.log('updated length');
      console.log(newvalue);
      $scope.updateRegisteredEvents();
    }
  });

  $scope.othersRegisteredEvents = [];
  $scope.registeredEvents = [];
 
  $scope.updateRegisteredEvents = function() {
    $scope.registeredEvents.length = 0;
    var addToRegistered = function(course){
      $scope.registeredEvents.push(course.toEvent("registered"));
    };
    angular.forEach($scope.selectedChild.registered, function(courseId){
      CoursesService.get(courseId).then(addToRegistered);
    });
  };
  
  $scope.updateOthersEvents = function(){
    $scope.othersRegisteredEvents.length = 0;
    var addToOthers = function(course){
      $scope.othersRegisteredEvents.push(course.toEvent("unavailable"));
    };
    angular.forEach($scope.userChildren, function(child){
      if (child !== $scope.selectedChild) {
        angular.forEach($scope['registeredCourses_' + child.id], function(courseId){
          CoursesService.get(courseId).then(addToOthers);
        });
      }
     }); 
  };
   
  $scope.sendRegisteredCourses = function(){
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
    
})

/*******************************************************************************
                    List of activities, on the left.
*******************************************************************************/
.controller('ActivityListCtrl', function($scope) {
  'use strict';
})

/*******************************************************************************
                    Timeline

*******************************************************************************/
.controller('ActivityTimelineCtrl', function($scope, $filter, $modal, CoursesService){
  'use strict';
  var today = new Date();
  var year = today.getFullYear();
  var month = today.getMonth();
  var day = today.getDate();
  // this controler is reloaded each time an activity is changed
  $scope.availableEvents = [];
  
  $scope.updateCalUI = function(){
    $scope.weekagenda.fullCalendar('refetchEvents');
  }
  
  
  $scope.$watch('selectedActivity', function(){
    if (!angular.isDefined($scope.selectedActivity)){
      return;
    }

    var addCourse = function(course){
      var start = new Date(year, month, day + (course.day - today.getDay()), 
                           course.start_time.split(':')[0], course.start_time.split(':')[1]);
      var end = new Date(year, month, day + (course.day - today.getDay()), 
                           course.end_time.split(':')[0], course.end_time.split(':')[1]);
      $scope.availableEvents.push({
         title: course.activity.name,
         start: start, end: end, allDay: false,
         className: "available", course: course,
         activityId: course.activity.id
      });
    };
    
    $scope.availableEvents.length = 0;
    angular.forEach($scope.selectedActivity.courses, function(course){
      var registered = $scope.selectedChild.hasRegistered(course);
      var available = course.schoolyear_min <= $scope.selectedChild.school_year &&
                      course.schoolyear_max >= $scope.selectedChild.school_year;
      if (!registered && available){
        CoursesService.get(course.id).then(addCourse);
      }
    });
  });
    
  $scope.eventClick = function(calEvent, jsEvent, view){
      $scope.$apply(function(){
        $scope.selectedEvent = calEvent;
        $scope.selectedCourse = calEvent.course;
        
        var modal = $modal(
            {template: '/static/partials/activity-detail.html',
             show: true,
             backdrop: 'static',
             scope: $scope,
        });
      });
  }
  
  $scope.uiConfig = {
    calendar:{
      height: 450, aspectRatio: 2, editable: false,
      year: year, month: month, date: day,
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
  
  
  $scope.register = function(calEvent){
    var courseId = calEvent.course.id;
    if (!$scope.selectedChild.canRegister(calEvent.course)){
      return;
    }
    var index = $scope.selectedChild.registered.indexOf(courseId);
    if (index === -1){
        // unregistered event, register it
        calEvent.className = 'registered';
        $scope.selectedChild.registered.push(courseId);
        console.log($scope.selectedChild.registered);
    }
    
  };
  
  $scope.unregister = function(calEvent){
    var courseId = calEvent.course.id;
    var index = $scope.selectedChild.registered.indexOf(courseId);

    // dont change this == to a === it won't work. Dunno why.
    if (calEvent.className == 'registered') {
        // registered to this child
        calEvent.className = 'available';
        $scope.selectedChild.registered.splice(index, 1);
        if (calEvent.activityId !== $scope.activityId){
            $scope.weekagenda.fullCalendar('removeEvents', calEvent._id);
        } else{
            $scope.weekagenda.fullCalendar('updateEvent', calEvent);
        }
    } else {
        alert('other child, no implemented yet');
        // registered to another child
    }
  }

  $scope.eventSources = [$scope.registeredEvents, $scope.othersRegisteredEvents, $scope.availableEvents];
})
  .controller('ActivityDetailCtrl', function($scope){
  /*****************************************************************************
                    Detailed activity

  *****************************************************************************/
  'use strict';

  });