angular.module('sportfacCalendar.controllers', [])

.controller('ChildrenCtrl', ["$scope", "$routeParams", "$attrs", "$location", "$window", "$document",
                             "$filter", "ChildrenService", "RegistrationsService", "WaitingSlotService",
function($scope, $routeParams, $attrs, $location, $window, $document,
         $filter, ChildrenService, RegistrationsService, WaitingSlotService) {
  'use strict';
  // Helper function to parse boolean attributes
  const parseBooleanAttr = (attrValue) => attrValue === 'true';
  const requiredAttrs = ['maxregistrations', 'starthour', 'endhour', 'displaydates',
                                 'displaycoursenames', 'limitbyschoolyear'];
  requiredAttrs.forEach(attr => {
    if (!$attrs[attr]) throw new Error(`No ${attr} option set`);
  });
  // Parse and set scope attributes
  $scope.maxregistrations = parseInt($attrs.maxregistrations, 10);
  $scope.startHour = parseInt($attrs.starthour, 10);
  $scope.endHour = parseInt($attrs.endhour, 10);
  $scope.displaydates = parseBooleanAttr($attrs.displaydates);
  $scope.displaycoursenames = parseBooleanAttr($attrs.displaycoursenames);
  $scope.canregistersameactivity = parseBooleanAttr($attrs.canregistersameactivity || 'false');
  $scope.usewaitingslots = !($attrs.usewaitingslots === 'false');
  $scope.limitbyschoolyear = parseBooleanAttr($attrs.limitbyschoolyear);
  $scope.hiddenDays = $attrs.hiddendays ? JSON.parse($attrs.hiddendays) : [];

  $scope.urls = {
    activity: $attrs.activityserviceurl,
    child: $attrs.childserviceurl,
    course: $attrs.courseserviceurl,
    family: $attrs.familyserviceurl,
    registration: $attrs.registrationserviceurl,
    waitingSlots: $attrs.waitingslotsserviceurl,
  };

  // Load registrations and waiting slots
  $scope.loadRegistrations = () => {
    RegistrationsService.all($scope.urls.registration).then(registrations => {
      $scope.registrations = registrations;
    });
  };

  $scope.loadWaitingSlots = () => {
    WaitingSlotService.all($scope.urls.waitingslots).then(slots => {
      $scope.waitingSlots = slots;
    });
  };

  $scope.getRegistrations = (child) => {
    return $scope.registrations?.filter(registration => registration.child === child.id);
  };

  // Unregister a course for a child
  $scope.unregisterCourse = (child, course) => {
    const registration = $scope.registrations.find(reg => reg.child === child.id && reg.course === course.id);
    if (registration) {
      RegistrationsService.del($scope.urls.registration, registration);
      $scope.registrations = $scope.registrations.filter(reg => reg !== registration);
    }
  };

  // Register a child for a course
  $scope.registerCourse = (child, course) => {
    const registration = { child: child.id, course: course.id };
    RegistrationsService.save($scope.urls.registration, registration).then(() => {
      $scope.registrations.push(registration);
    });
  };

  // Add a child to the waiting list for a course
  $scope.addToWaitingList = (course, child) => {
    const slot = { child: child.id, course: course.id };
    WaitingSlotService.create($scope.urls.waitingslots, slot).then(() => {
      $scope.waitingSlots.push(slot);
    });
  };

 // Check if a child is on the waiting list for a course
  $scope.isOnWaitingList = (course, child) => {
    return $scope.waitingSlots?.some(slot => slot.child === child.id && slot.course === course.id);
  };

  // Remove a child from the waiting list
  $scope.removeFromWaitingList = (course, child) => {
    const slot = $scope.waitingSlots.find(slot => slot.child === child.id && slot.course === course.id);
    if (slot) {
      WaitingSlotService.del($scope.urls.waitingslots, slot);
      $scope.waitingSlots = $scope.waitingSlots.filter(s => s !== slot);
    }
  };

  // Select a specific child
  $scope.selectChild = (childId) => {
    $scope.userChildren.forEach(child => {
      child.selected = (child.id === childId);
      if (child.selected) $scope.selectedChild = child;
    });
  };

  // Load user children and initialize data
  ChildrenService.all($scope.urls.family).then(children => {
    $scope.userChildren = children;
    let childId = parseInt($routeParams.childId, 10) || $scope.userChildren[0].id;
    if (isNaN(childId)) {
      childId = $scope.userChildren[0].id;
      $location.path(`/child/${childId}/`);
    }
    $scope.selectChild(childId);
    $scope.loadRegistrations();
    $scope.loadWaitingSlots();
  });

  $scope.confirmNavigation = (event) => {
    event.preventDefault(); // Prevent default link behavior
    // Check if there are any children without a registration
    $scope.childrenWithoutRegistration = $scope.userChildren.filter(
      child => !$scope.registrations.some(reg => reg.child === child.id)
    );
    if ($scope.childrenWithoutRegistration.length === 0) {
      $scope.navigateToNextStep();
    } else {
      $scope.nextStepUrl = event.currentTarget.getAttribute('data-url');
      $('#confirmModal').modal('show');
      $document.on('keydown', $scope.handleKeyPress);
    }
  };

  $scope.handleKeyPress = (event) => {
    const keyActionMap = {
      13: () => document.getElementById('modalYes').click(),  // Enter key
      27: () => document.getElementById('modalNo').click()    // Escape key
    };
    if (keyActionMap[event.keyCode]) keyActionMap[event.keyCode]();
  };

  $scope.navigateToNextStep = () => {
    $('#confirmModal').modal('hide');
    $window.location.href = $scope.nextStepUrl;
  };

  // Clean up event listener when modal is hidden
  $('#confirmModal').on('hidden.bs.modal', () => {
    $document.off('keydown', $scope.handleKeyPress);
  });

}])


/*******************************************************************************
        Activities management, i.e. a child tab in activities application
*******************************************************************************/
.controller('ActivityCtrl', ["$scope", "$http", function($scope, $http) {
  'use strict';

  // Watch for changes in the selected child
  $scope.$watch('selectedChild', (newChild) => {
    if (angular.isDefined(newChild)) {
      loadActivitiesForChild(newChild);
      $scope.selectedActivity = {}; // Reset selected activity when child changes
    }
  });

  // Function to select an activity
  $scope.selectActivity = (activity) => {
    if ($scope.selectedActivity) {
      $scope.selectedActivity.selected = false; // Unselect previous activity
    }
    activity.selected = true; // Mark new activity as selected
    $scope.selectedActivity = activity; // Set as the current selected activity
  };

  // Load activities for the selected child
  const loadActivitiesForChild = (child) => {
    const url = `${$scope.urls.activity}?year=${child.school_year}&birth_date=${child.birth_date}`;
    $http({ method: 'GET', url, cache: true })
      .then((response) => {
        $scope.activities = response.data;
      })
      .catch((error) => {
        console.error("Failed to load activities", error);
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
        if (event1.all_day || event2.all_day) {
          // common dates. if a single lasts all day, overlap is certain
          return true;
        }
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
