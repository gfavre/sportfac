angular.module('sportfacCalendar.controllers', [])

.controller('ChildrenCtrl', ["$scope", "$routeParams", "$attrs", "$location", "$filter", "ChildrenService", "RegistrationsService",
function($scope, $routeParams, $attrs, $location, $filter, ChildrenService, RegistrationsService) {
  'use strict';
  if (!$attrs.maxregistrations) throw new Error("No maxregistrations option set");
    $scope.maxregistrations = parseInt($attrs.maxregistrations);
  if (!$attrs.starthour) throw new Error("No starthour option set");
    $scope.startHour = parseInt($attrs.starthour);
  if (!$attrs.endhour) throw new Error("No endhour option set");
    $scope.endHour = parseInt($attrs.endhour);
  if (!$attrs.displaydates) throw new Error("No displaydates option set");
    $scope.displaydates = $attrs.displaydates === 'true';
  if (!$attrs.displaycoursenames) throw new Error("No displaycoursenames option set");
    $scope.displaycoursenames = $attrs.displaycoursenames === 'true';
  if ($attrs.canregistersameactivity){
    $scope.canregistersameactivity = $attrs.canregistersameactivity === 'true';
  } else {
    $scope.canregistersameactivity = false;
  }
  if (!$attrs.limitbyschoolyear) throw new Error("No limitbyschoolyear option set");
    $scope.limitbyschoolyear = $attrs.limitbyschoolyear === 'true';
  if ($attrs.hiddendays) {
     $scope.hiddenDays = JSON.parse($attrs.hiddendays);
  } else {
    $scope.hiddenDays = [];
  }
  
  $scope.urls = {
    activity: $attrs.activityserviceurl,
    child: $attrs.childserviceurl,
    course: $attrs.courseserviceurl,
    family: $attrs.familyserviceurl,
    registration: $attrs.registrationserviceurl
  };

  $scope.loadRegistrations = function(){
    RegistrationsService.all($scope.urls.registration).then(function(registrations){
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
    RegistrationsService.del($scope.urls.registration, registration);
    $scope.registrations.remove(registration);
  };

  $scope.registerCourse = function(child, course){
    var registration = {child: child.id, course: course.id};
    RegistrationsService.save($scope.urls.registration, registration).then(function(){
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

  ChildrenService.all($scope.urls.family).then(function(children){
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
    let url = $scope.urls.activity + '?year=' + $scope.selectedChild.school_year + '&birth_date=' + $scope.selectedChild.birth_date;
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
.controller('ActivityTimelineCtrl', ["$scope","$filter", "$modal", "CoursesService", 'uiCalendarConfig',
function($scope, $filter, $modal, CoursesService, uiCalendarConfig){
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

  $scope.overlap = function(event1, event2){
    // Two dates overlap if StartA <= EndB and startB <= EndA
    // Here wee need periods to overlap and running day to be the same.
    // Moreover, times of day should overlap
    var start1 = new Date(event1.start_date);
    var start2 = new Date(event2.start_date);
    var end1   = new Date(event1.end_date);
    var end2   = new Date(event2.end_date);
    if (( start1 <= end2 ) && (start2 <= end1) && event1.day === event2.day) {
      // dates overlap. Let's see if times overlap
      return event1.start_time <= event2.end_time && event2.start_time <= event1.end_time;
    }
    return false;
  };

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
      var events = course.toEvents('registered');
      angular.forEach(events, function (event) {
        event.registeredChild = $scope.selectedChild;
        $scope.registeredEvents.push(event);
      });
      // $scope.registeredEvents.push.apply($scope.registeredEvents, event);
    };
    var addToValidated = function(course){
      var events = course.toEvents('validated');
      angular.forEach(events, function (event) {
        event.registeredChild = $scope.selectedChild;
        $scope.registeredEvents.push(event);
      });
    };
    angular.forEach($scope.getRegistrations($scope.selectedChild), function(registration){
      if (registration.status === 'valid'){
          CoursesService.get($scope.urls.course, registration.course).then(addToValidated);
      } else {
          CoursesService.get($scope.urls.course, registration.course).then(addToRegistered);
      }

    });
  };


  $scope.updateOthersEvents = function(){
    if (!$scope.registrations){
      return;
    }

    $scope.othersRegisteredEvents.length = 0;
    angular.forEach($scope.userChildren, function(child){
      if (child !== $scope.selectedChild){
        angular.forEach($scope.getRegistrations(child), function(registration){
          CoursesService.get($scope.urls.course, registration.course).then(function(course){
            var events = course.toEvents("unavailable");
            angular.forEach(events, function(event){
              event.registeredChild = child;
            })
            $scope.othersRegisteredEvents.push.apply($scope.othersRegisteredEvents, events);
          });
        });
      }
     });
  };

  $scope.updateAvailableEvents = function(){
    var addAvailableCourse = function(course){
      $scope.availableEvents.push.apply($scope.availableEvents, course.toEvents("available"));
    };
    var addUnavailableCourse = function(course){
      $scope.availableEvents.push.apply($scope.availableEvents, course.toEvents("unavailable"));
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
      if ((registeredCourses.indexOf(course.id) !== -1) && !$scope.canregistersameactivity) {
        activityRegistered = true;
      }
    });

    angular.forEach($scope.selectedActivity.courses, function(course){
      if ($scope.limitbyschoolyear) {
        var available = course.schoolyear_min <= $scope.selectedChild.school_year &&
          course.schoolyear_max >= $scope.selectedChild.school_year;
      } else {
         var available = course.min_birth_date >= $scope.selectedChild.birth_date && course.max_birth_date <= $scope.selectedChild.birth_date;
      }
      var registered = registeredCourses.indexOf(course.id) !== -1;
      var overlapping = $scope.registeredEvents.map(
        function(evt){
          return $scope.overlap(evt.course, course);
        }
      ).reduce(function(overlap1, overlap2) {
          return overlap1 || overlap2;
      }, false);

      if (!registered && available){
        if (activityRegistered || overlapping){
          CoursesService.get($scope.urls.course, course.id).then(addUnavailableCourse);
          //addUnavailableCourse(course);
        } else {
          CoursesService.get($scope.urls.course, course.id).then(addAvailableCourse);
          //addAvailableCourse(course);

        }
      }
    });
  };

  $scope.eventClick = function(event, element, evt, view){
      $scope.$apply(function(){
        if (!event.clickable){ return; }
        $scope.selectedEvent = event;
        $scope.selectedCourse = event.course;
        modalwindow.show();
      });
  };

  $scope.eventMouseEnter = function(event, evt, element, view){
    if (event.course.course_type != 'multicourse') return;
    evt.preventDefault();
    var $event = $(this);
    if (!$event.hasClass('selected')){
      var groupId = event.groupId;
      $('[groupId=' + groupId + ']', $($scope.weekagenda)).addClass('selected')
    }
  };

  $scope.eventMouseLeave = function(event, element, evt){
    if (event.course.course_type != 'multicourse') return;
    var $event = $(this);

    if ($event.hasClass('selected')){
      var groupId = event.groupId;
      $('[groupId=' + groupId + ']', $($scope.weekagenda)).removeClass('selected')
    }
  };

  $scope.register = function(event){
    if (!$scope.selectedChild.canRegister(event.course, $scope.limitbyschoolyear)){
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

  $scope.slotMinutes = 15;
  if (($scope.endHour - $scope.startHour) % 24 > 8) {
      $scope.slotMinutes = 30;
  }

  $scope.uiConfig = {
    calendar:{
      height: 650, aspectRatio: 3, editable: false,
      year: year, month: month, date: day,


      defaultView: 'agendaWeek', weekends: true, firstDay:1, allDaySlot: false,
      hiddenDays: $scope.hiddenDays,
      slotMinutes: $scope.slotMinutes, maxTime: $scope.endHour, minTime: $scope.startHour,
      axisFormat: 'H:mm', columnFormat: 'dddd',
      header:{left: 'prev,next', center: '', right: 'agendaWeek,agendaDay'},
      buttonText: {
        prev: '<', next: '>', today: "Aujourd'hui", month: 'Mois', week: 'Semaine', day: 'Jour'
      },
      dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
      dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
      timeFormat: {agenda: 'd'}, lazyFetching: true,
      eventClick: $scope.eventClick,
      eventMouseover: $scope.eventMouseEnter,
      eventMouseout: $scope.eventMouseLeave,
      eventRender : function(event, element) {
         $(element).tooltip({html: true, title: event.title + '<br>' + $filter('date')(event.course.start_date, 'dd.MM.yyyy') + '&nbsp;-&nbsp;' + $filter('date')(event.course.end_date, 'dd.MM.yyyy'), });
      },
      slotEventOverlap: false,
      eventAfterRender: function(event, element) {
        var dateText = '';
        if ($scope.displaydates) {
          dateText = $filter('date')(event.course.start_date, 'shortDate') + ' - ' + $filter('date')(event.course.end_date, 'shortDate');
        }
        $(element).attr('id', event.id);
        $(element).attr('groupId', event.groupId);
        $('.fc-event-time', element).text(dateText);
        if ($scope.displaycoursenames && event.course.name !== null) {
          /* commented out: perhaps an overkill.
          var timeDiff = Math.abs(event.course.getEndDate().getTime() - event.course.getStartDate().getTime());
          var diffHours = timeDiff / (1000 * 3600 );
          if (diffHours >= 2) {*/
            $('.fc-event-title', element).after('<div class="fc-event-course">' + event.course.name + '</div>');
          /*}*/
        }

        /* Commented out: graphically not adapted
        if (angular.isDefined(event.registeredChild)){
            $('.fc-event-title', element).after('<div class="fc-event-child">' + event.registeredChild.first_name + '</div>');
        }*/
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
