angular.module('sportfacCalendar.controllers', [])

.controller('ChildrenCtrl', ["$scope", "$routeParams", "$attrs", "$location", "$filter", "ChildrenService", "RegistrationsService", "WaitingSlotService",
function($scope, $routeParams, $attrs, $location, $filter, ChildrenService, RegistrationsService, WaitingSlotService) {
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
  $scope.usewaitingslots = true;
  if ($attrs.usewaitingslots && $attrs.usewaitingslots === 'false'){
    $scope.usewaitingslots = false;
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
    registration: $attrs.registrationserviceurl,
    waitingslots: $attrs.waitingslotsserviceurl,
  };

  $scope.loadRegistrations = function(){
    RegistrationsService.all($scope.urls.registration).then(function(registrations){
      $scope.registrations = registrations;
    });
  };
  $scope.loadWaitingSlots = function(){
    WaitingSlotService.all($scope.urls.waitingslots).then(function(slots){
      $scope.waitingSlots = slots;
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
    let compare = function(registration){
       return registration.child === child.id && registration.course === course.id;
    };

    let registration = $filter('filter')($scope.registrations, compare)[0];
    RegistrationsService.del($scope.urls.registration, registration);
    $scope.registrations.remove(registration);
  };

  $scope.registerCourse = function(child, course){
    let registration = {child: child.id, course: course.id};
    RegistrationsService.save($scope.urls.registration, registration).then(function(){
      $scope.registrations.push(registration);
    });
  };

  $scope.addToWaitingList = function(course, child){
    let slot = {child: child.id, course: course.id};
    WaitingSlotService.create($scope.urls.waitingslots, slot).then(function(){
      $scope.waitingSlots.push(slot);
    });
  };
  $scope.isOnWaitingList = function(course, child){
    let compare = function(slot){
       return slot.child === child.id && slot.course === course.id;
    };
    return $filter('filter')($scope.waitingSlots, compare).length === 1;
  }
  $scope.removeFromWaitingList = function(course, child){
    let compare = function(slot){
       return slot.child === child.id && slot.course === course.id;
    };

    let slot = $filter('filter')($scope.waitingSlots, compare)[0];
    WaitingSlotService.del($scope.urls.waitingslots, slot);
    $scope.waitingSlots.remove(slot);
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
    $scope.loadWaitingSlots();
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
  let today = new Date();
  let year = today.getFullYear();
  let month = today.getMonth();
  let day = today.getDate();

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
    let set1 = new Set(event1.all_dates);
    let set2 = new Set(event2.all_dates);

    // Check if there are any common dates
    let commonDates = [...set1].filter(date => set2.has(date));
    if (commonDates.length > 0) {
        // There are common dates, now check if times overlap
        // Convert times to comparable format, assuming event1.start_time, etc., are in 'HH:MM' format
        let startTime1 = event1.start_time.split(':').map(Number);
        let endTime1 = event1.end_time.split(':').map(Number);
        let startTime2 = event2.start_time.split(':').map(Number);
        let endTime2 = event2.end_time.split(':').map(Number);

        // Compare times
        let start1 = new Date(0, 0, 0, startTime1[0], startTime1[1]);
        let end1 = new Date(0, 0, 0, endTime1[0], endTime1[1]);
        let start2 = new Date(0, 0, 0, startTime2[0], startTime2[1]);
        let end2 = new Date(0, 0, 0, endTime2[0], endTime2[1]);
        return start1 <= end2 && start2 <= end1;
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

  let addAvailableCourse = function(course){
    // je passe ici le bon nombre de fois, tous les cours sont ajoutés.
    $scope.availableEvents.push.apply($scope.availableEvents, course.toEvents("available"));
  };
  let addUnavailableCourse = function(course){
    $scope.availableEvents.push.apply($scope.availableEvents, course.toEvents("unavailable"));
  };

  $scope.updateRegisteredEvents = function() {
    if (!$scope.registrations){ return; }
    $scope.registeredEvents.length = 0;
    let addToRegistered = function(course){
      let events = course.toEvents('registered');
      angular.forEach(events, function (event) {
        event.registeredChild = $scope.selectedChild;
        $scope.registeredEvents.push(event);
      });
      // $scope.registeredEvents.push.apply($scope.registeredEvents, event);
    };
    let addToValidated = function(course){
      let events = course.toEvents('validated');
      angular.forEach(events, function (event) {
        event.registeredChild = $scope.selectedChild;
        $scope.registeredEvents.push(event);
      });
    };
    angular.forEach($scope.getRegistrations($scope.selectedChild), function(registration){
      $scope.registeredEventsToFetch += 1;
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
          $scope.othersRegisteredEventsToFetch += 1;
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
    $scope.availableEvents.length = 0;

    let registeredCourses = $scope.getRegistrations($scope.selectedChild);
    if (registeredCourses){
      registeredCourses = registeredCourses.map(function(registration){
        return registration.course;
      });
    }

    let activityRegistered = false;

    angular.forEach($scope.selectedActivity.courses, function(course){

      if ((registeredCourses.indexOf(course.id) !== -1) && !$scope.canregistersameactivity) {
        activityRegistered = true;
      }
      let available = false;
      if ($scope.limitbyschoolyear) {
        available = course.schoolyear_min <= $scope.selectedChild.school_year &&
          course.schoolyear_max >= $scope.selectedChild.school_year;
      } else {
         available = course.min_birth_date >= $scope.selectedChild.birth_date &&
           course.max_birth_date <= $scope.selectedChild.birth_date;
      }
      let registered = registeredCourses.indexOf(course.id) !== -1;
      let overlapping = $scope.registeredEvents.map(
        function(evt){
          return $scope.overlap(evt.course, course);
        }
      ).reduce(function(overlap1, overlap2) {
          return overlap1 || overlap2;
      }, false);
      if (!registered && available){
        $scope.availableEventsToFetch += 1;
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
  $scope.othersRegisteredEventsToFetch = 0;
  $scope.registeredEvents = [];
  $scope.registeredEventsToFetch = 0;
  $scope.availableEvents = [];
  $scope.availableEventsToFetch = 0;
  $scope.eventSources = [$scope.registeredEvents, $scope.othersRegisteredEvents, $scope.availableEvents];


  /* This section ensures ordering of events in the calendar. */
  $scope.$watch('othersRegisteredEvents.length', function(newLength, old_length){
    if ($scope.othersRegisteredEventsToFetch > 0 && newLength === $scope.othersRegisteredEventsToFetch) {
      $scope.othersRegisteredEventsToFetch = 0;
      $scope.othersRegisteredEvents.sort(function (event1, event2) {
        return event1.course.start_date.localeCompare(event2.course.start_date);
      });
    }
  });

  $scope.$watch('registeredEvents.length', function(newLength, old_length){
    if ($scope.registeredEventsToFetch > 0 && newLength === $scope.registeredEventsToFetch) {
      $scope.registeredEventsToFetch = 0;
      $scope.registeredEvents.sort(function (event1, event2) {
        return event1.course.start_date.localeCompare(event2.course.start_date);
      });
    }
  });

  $scope.$watch('availableEvents.length', function(newLength, old_length){
    if ($scope.availableEventsToFetch > 0 && newLength === $scope.availableEventsToFetch) {
      $scope.availableEventsToFetch = 0;
      $scope.availableEvents.sort(function (event1, event2) {
        return event1.course.start_date.localeCompare(event2.course.start_date);
      });
    }
  });




}])


/*****************************************************************************
                    Detailed activity
*****************************************************************************/
.controller('ActivityDetailCtrl', ["$scope", function($scope){
  'use strict';

}]);
