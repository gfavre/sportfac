angular.module('sportfacCalendar.controllers', [])
  
.controller('ChildrenCtrl', ["$scope", "$routeParams", "$attrs", "$location", "$filter", "ChildrenService", "RegistrationsService",
function($scope, $routeParams, $attrs, $location, $filter, ChildrenService, RegistrationsService) {
  'use strict';
  if (!$attrs.maxregistrations) throw new Error("No maxregistrations option set");
    $scope.maxregistrations = parseInt($attrs.maxregistrations);
  
  $scope.loadRegistrations = function(){
    RegistrationsService.all().then(function(registrations){
      $scope.registrations = registrations;
    });
  };
  
  $scope.getRegistrations = function(child){
    if (!angular.isDefined($scope.registrations)){
      return;
    }
    var compare = function(registration){
      return registration.child === child.id;
    };
    return $filter('filter')($scope.registrations, compare);
  };
   
  $scope.unregisterCourse = function(child, course){
    var compare = function(registration){
       return registration.child === child.id && registration.course === course.id;
    };
    
    var registration = $filter('filter')($scope.registrations, compare)[0];
    RegistrationsService.del(registration);
    $scope.registrations.remove(registration);
  };
  
  $scope.registerCourse = function(child, course){
    var registration = {child: child.id, course: course.id};
    RegistrationsService.save(registration).then(function(){
      $scope.registrations.push(registration);
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
  };
    
  ChildrenService.all().then(function(children){
    $scope.userChildren = children;
    var childId = parseInt($routeParams.childId, 10);
    if (isNaN(childId)) {
      childId = $scope.userChildren[0].id;
      $location.path('/child/' + $scope.userChildren[0].id + '/');
    }
    $scope.selectChild(childId);
    $scope.loadRegistrations();
  });

}])


/*******************************************************************************
        Activities management, i.e. a child tab in activities application
*******************************************************************************/
.controller('ActivityCtrl', ["$scope", "$http", function($scope, $http) {
  'use strict';
  $scope.$watch('selectedChild', function(){
    if (angular.isDefined($scope.selectedChild) ){
      $scope.loadActivities();
      $scope.selectedActivity = {};
    }
  });
  
  $scope.selectActivity = function(activity){
    if ($scope.selectedActivity) { $scope.selectedActivity.selected = false;}
    activity.selected = true;
    $scope.selectedActivity = activity;
  };
  
  $scope.loadActivities = function(){
    var url = '/api/activities/?year=' + $scope.selectedChild.school_year;
    $http({method: 'GET', url: url, cache: true})
       .success(function(response){
           $scope.activities = response;
       });
  };
}])


/*******************************************************************************
                    List of activities, on the left.
*******************************************************************************/
.controller('ActivityListCtrl', [function() {
  'use strict';
}])


/*******************************************************************************
                    Timeline
*******************************************************************************/
.controller('ActivityTimelineCtrl', ["$scope", "$filter", "$modal", "CoursesService",
function($scope, $filter, $modal, CoursesService){
  'use strict';
  var today = new Date();
  var year = today.getFullYear();
  var month = today.getMonth();
  var day = today.getDate();
  
  var modalwindow = $modal(
            {template: '/static/partials/activity-detail.html',
             show: false,
             backdrop: 'static',
             persist: true,
             keyboard: true,
             container: 'body',
             animation: "am-flip-x",
             scope: $scope,
  });
  
  
  $scope.$watch('registrations.length', function(){
    if (!angular.isDefined($scope.registrations)){ return; }
    
    $scope.updateAvailableEvents();
    $scope.updateRegisteredEvents();
    $scope.updateOthersEvents();
  });
  
  $scope.$watch('selectedActivity', function(){
    if (angular.isDefined($scope.selectedActivity)){
      $scope.updateAvailableEvents();
    }
  });
  
  $scope.updateRegisteredEvents = function() {
    if (!$scope.registrations){ return; }
    $scope.registeredEvents.length = 0;
    var addToRegistered = function(course){
      var event = course.toEvent('registered');
      event.registeredChild = $scope.selectedChild;
      $scope.registeredEvents.push(event);
    };
    var addToValidated = function(course){
      var event = course.toEvent('validated');
      event.registeredChild = $scope.selectedChild;
      $scope.registeredEvents.push(event);
    };
    angular.forEach($scope.getRegistrations($scope.selectedChild), function(registration){
      if (registration.status === 'valid'){
          CoursesService.get(registration.course).then(addToValidated);
      } else {
          CoursesService.get(registration.course).then(addToRegistered);
      }
      
    });
  };
  
  
  $scope.updateOthersEvents = function(){
    if (!$scope.registrations){
      return;
    }
    
    $scope.othersRegisteredEvents.length = 0;
    angular.forEach($scope.userChildren, function(child){
      if (child !== $scope.selectedChild) {
        angular.forEach($scope.getRegistrations(child), function(registration){
          CoursesService.get(registration.course).then(function(course){
            var event = course.toEvent("unavailable");
            event.registeredChild = child;
            $scope.othersRegisteredEvents.push(event);
          });
        });
      }
     });
     
  };
  
  $scope.updateAvailableEvents = function(){
    var addAvailableCourse = function(course){
      $scope.availableEvents.push(course.toEvent("available"));
    };
    var addUnavailableCourse = function(course){
      $scope.availableEvents.push(course.toEvent("unavailable"));
    };
    var registeredCourses = $scope.getRegistrations($scope.selectedChild);
    if (registeredCourses){
      registeredCourses = registeredCourses.map(function(registration){
        return registration.course;
      });
    }
    
    $scope.availableEvents.length = 0;
    
    var activityRegistered = false;
    angular.forEach($scope.selectedActivity.courses, function(course){
      if (registeredCourses.indexOf(course.id) !== -1){
        activityRegistered = true;
      }
    });
    angular.forEach($scope.selectedActivity.courses, function(course){
      var available = course.schoolyear_min <= $scope.selectedChild.school_year &&
                      course.schoolyear_max >= $scope.selectedChild.school_year;
      var registered = registeredCourses.indexOf(course.id) !== -1;
      if (!registered && available){
        if (activityRegistered){
          CoursesService.get(course.id).then(addUnavailableCourse);
        } else {
          CoursesService.get(course.id).then(addAvailableCourse);
        }
      }
    });
  };

  $scope.eventClick = function(event){
      $scope.$apply(function(){
        if (!event.clickable){ return; }
        $scope.selectedEvent = event;
        $scope.selectedCourse = event.course;
        modalwindow.show();
      });
  };
  
    
  
  $scope.register = function(event){
    if (!$scope.selectedChild.canRegister(event.course)){
      return;
    }
    $scope.registerCourse($scope.selectedChild, event.course);
  };
  
  $scope.unregister = function(event){
    $scope.unregisterCourse($scope.selectedChild, event.course);
        
    if (event.clickable) {
        // registered to this child
        event.className = 'available';
        if (event.activityId !== $scope.activityId){
            $scope.weekagenda.fullCalendar('removeEvents', event._id);
        } else{
            $scope.weekagenda.fullCalendar('updateEvent', event);
        }
    }
  };
  
  $scope.hasRegistered = function(){
    return $scope.registeredEvents.length > 0 || $scope.othersRegisteredEvents.length > 0;
  };



  $scope.uiConfig = {
    calendar:{
      height: 650, aspectRatio: 3, editable: false,
      year: year, month: month, date: day,
      defaultView: 'agendaWeek', weekends: false, allDaySlot: false,
      slotMinutes: 15, maxTime: 19, minTime: 11,
      axisFormat: 'H:mm', columnFormat: 'dddd', header:{left: '', center: '', right: ''},
      dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
      dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
      timeFormat: {agenda: 'd'}, lazyFetching: true,
      eventClick: $scope.eventClick,
      eventAfterRender: function(event, element){
        var text = $filter('date')(event.course.start_date, 'shortDate') +' - ' + $filter('date')(event.course.end_date, 'shortDate');
        $('.fc-event-time', element).text(text);
        if (angular.isDefined(event.registeredChild)){
            $('.fc-event-title', element).after('<div class="fc-event-child">' + event.registeredChild.first_name + '</div>');
        }
        
      }
    }
  };

  $scope.othersRegisteredEvents = [];
  $scope.registeredEvents = [];
  $scope.availableEvents = [];
  $scope.eventSources = [$scope.registeredEvents, $scope.othersRegisteredEvents, $scope.availableEvents];
}])


/*****************************************************************************
                    Detailed activity
*****************************************************************************/
.controller('ActivityDetailCtrl', [function(){
  'use strict';
}]);