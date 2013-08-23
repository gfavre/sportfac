angular.module('sportfacCalendar.controllers', [])
  
.controller('ChildrenCtrl', ["$scope", "$routeParams", "$location", "$filter", "ChildrenService", "RegistrationsService",
function($scope, $routeParams, $location, $filter, ChildrenService, RegistrationsService) {
  'use strict';
  
  $scope.loadRegistrations = function(){
    RegistrationsService.all().then(function(registrations){
      $scope.registrations = registrations;
    });
  };
  
  $scope.getRegisteredCourses = function(child){
    if (!angular.isDefined($scope.registrations)){
      return;
    }
    return $filter('filter')($scope.registrations, {child: child.id}).map(
                function(registration){
                    return registration.course;
                });
  };
   
  $scope.unregisterCourse = function(child, course){
    var registration = $filter('filter')($scope.registrations, {child: child.id, course: course.id})[0];
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
.controller('ActivityCtrl', ["$scope", "$http",
function($scope, $http) {
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
    $scope.activities = $http({method: 'GET', url: url, cache: true}).then(function(response){
        return response.data;
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
      var event = course.toEvent("registered");
      event.registeredChild = $scope.selectedChild;
      $scope.registeredEvents.push(event);
    };
    angular.forEach($scope.getRegisteredCourses($scope.selectedChild), function(courseId){
      CoursesService.get(courseId).then(addToRegistered);
    });
  };
  
  
  $scope.updateOthersEvents = function(){
    if (!$scope.registrations){
      return;
    }
    
    $scope.othersRegisteredEvents.length = 0;
    angular.forEach($scope.userChildren, function(child){
      if (child !== $scope.selectedChild) {
        angular.forEach($scope.getRegisteredCourses(child), function(courseId){
          CoursesService.get(courseId).then(function(course){
            var event = course.toEvent("unavailable");
            event.registeredChild = child;
            $scope.othersRegisteredEvents.push(event);
          });
        });
      }
     });
  };
  
  $scope.updateAvailableEvents = function(){
    var addCourse = function(course){
      $scope.availableEvents.push(course.toEvent("available"));
    };
    $scope.availableEvents.length = 0;
    angular.forEach($scope.selectedActivity.courses, function(course){
      var registered = $scope.getRegisteredCourses($scope.selectedChild).indexOf(course.id) !== -1;
      var available = course.schoolyear_min <= $scope.selectedChild.school_year &&
                      course.schoolyear_max >= $scope.selectedChild.school_year;
      if (!registered && available){
        CoursesService.get(course.id).then(addCourse);
      }
    });
  };

  $scope.eventClick = function(event){
      $scope.$apply(function(){
        if (!event.clickable){ return; }
        $scope.selectedEvent = event;
        $scope.selectedCourse = event.course;
        $modal(
            {template: '/static/partials/activity-detail.html',
             show: true,
             backdrop: 'static',
             scope: $scope,
        });
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
      height: 450, aspectRatio: 2, editable: false,
      year: year, month: month, date: day,
      defaultView: 'agendaWeek', weekends: false, allDaySlot: false,
      slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 13,
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