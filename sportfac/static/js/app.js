//'use strict';


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
var sportfacModule = angular.module('sportfac', ['sportfac.services', 'ui.calendar']);//['sportfac.filters', 'sportfac.services', 'sportfac.directives', 'ui.calendar']);

sportfacModule.factory("$store",function($parse){
 
  var storage = (typeof window.localStorage === 'undefined') ? undefined : window.localStorage,
      supported = !(typeof storage == 'undefined' || typeof window.JSON == 'undefined');
  
  var privateMethods = {
      /**
       * Pass any type of a string from the localStorage to be parsed so it returns a usable version (like an Object)
       * @param res - a string that will be parsed for type
       * @returns {*} - whatever the real type of stored value was
       */
      parseValue: function(res) {
      	var val;
      	try {
      		val = JSON.parse(res);
      		if (typeof val == 'undefined') val = res;
      		if (val == 'true') val = true;
      		if (val == 'false') val = false;
      		if (parseFloat(val) == val && !angular.isObject(val)) val = parseFloat(val);
      	} catch(e){
      		val = res;
      	}
      	return val;
      }
  };
  var publicMethods = {
      /**
       * Set - let's you set a new localStorage key pair set
       * @param key - a string that will be used as the accessor for the pair
       * @param value - the value of the localStorage item
       * @returns {*} - will return whatever it is you've stored in the local storage
       */
      set: function(key,value){
      	if (!supported){
      		try {
      			$.cookie(key, value);
      			return value;
      		} catch(e){
      			console.log('Local Storage not supported, make sure you have the $.cookie supported.');
      		}
      	}
      	var saver = JSON.stringify(value);
      	storage.setItem(key, saver);
      	return privateMethods.parseValue(saver);
      },
      /**
       * Get - let's you get the value of any pair you've stored
       * @param key - the string that you set as accessor for the pair
       * @returns {*} - Object,String,Float,Boolean depending on what you stored
       */
      get: function(key){
      	if (!supported){
      		try {
      			return privateMethods.parseValue($.cookie(key));
      		} catch(e){
      			return null;
      		}
      	}
      	var item = storage.getItem(key);
      	return privateMethods.parseValue(item);
      },
      /**
       * Remove - let's you nuke a value from localStorage
       * @param key - the accessor value
       * @returns {boolean} - if everything went as planned
       */
      remove: function(key) {
      	if (!supported){
      		try {
      			$.cookie(key, null);
      			return true;
      		} catch(e){
      			return false;
      		}
      	}
      	storage.removeItem(key);
      	return true;
      },
      /**
           * Bind - let's you directly bind a localStorage value to a $scope variable
           * @param $scope - the current scope you want the variable available in
           * @param key - the name of the variable you are binding
           * @param def - the default value (OPTIONAL)
           * @returns {*} - returns whatever the stored value is
           */
          bind: function ($scope, key) {
              if (!publicMethods.get(key)) {
                  publicMethods.set(key, []);
              }
              $parse(key).assign($scope, publicMethods.get(key));
              $scope.$watch(key, function (val) {
                  publicMethods.set(key, val);
              }, true);
              /*
              $scope.$watchCollection(key, function(newElems, oldElems){
                 publicMethods.set(key, newElems);
              });*/
              
              return $scope[key];
          }
  };
  return publicMethods;
});




sportfacModule.config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/activity/:activityId/timeline', 
        {templateUrl: '/static/partials/timeline.html', controller: 'ActivityTimelineCtrl'});
    
    $routeProvider.when('/activity/:activityId/detail', 
        {templateUrl: '/static/partials/activity-detail.html', controller: 'ActivityDetailCtrl'});
    
    $routeProvider.otherwise({redirectTo: '/activities'});
}]);

sportfacModule.config(function($interpolateProvider) {
  $interpolateProvider.startSymbol('{[{');
  $interpolateProvider.endSymbol('}]}');
});

var ActivityCtrl = function($scope, $http, $store) {
  
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
    var url = '/api/activities/' + activity_id
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
  }
  $scope.isAvailable = function(course){
    return !($scope.selectedChild.school_year < course.schoolyear_min || $scope.selectedChild.school_year > course.schoolyear_max);
  }
  
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
  
}



var ActivityListCtrl = function($scope, $http) {
  $scope.loadActivities = function(){
      var url = '/api/activities/?year=' + $scope.selectedChild.school_year;
      $scope.activities = $http({method: 'GET', url: url, cache: true}).then(function(response){
          return response.data;
      });
  };
  $scope.$watch('selectedChild', function(){ $scope.loadActivities()});
};



var ActivityTimelineCtrl = function($scope, $routeParams, $filter, $http){    
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
      $scope.registeredEvents.length = 0;
      for (var i=0; i<$scope.selectedChild.registered.length; i++) {
        $scope.getCourse($scope.selectedChild.registered[i], function(course){
          $scope.registeredEvents.push($scope.convertCourse(course, "registered"));
        });
      }
    };
    
    $scope.reloadOthersEvents = function(){
      $scope.othersEvents.length = 0;
      for (var i=0; i<$scope.othersRegisteredEvents.length; i++) {
        $scope.getCourse($scope.othersRegisteredEvents[i], function(course){
          $scope.registeredEvents.push($scope.convertCourse(course, "unavailable"));
        });
      }
    };
    
    $scope.changeActivity = function(activity){
      $scope.events.length = 0;
      
      for (var i=0; i<activity.courses.length; i++){
        var course = activity.courses[i];
        if ($scope.isRegistered(course)) continue;
        if (course.schoolyear_min > $scope.selectedChild.school_year || course.schoolyear_max < $scope.selectedChild.school_year) { continue };
        var start = new Date(y, m, d + (course.day - date.getDay()), course.start_time.split(':')[0], course.start_time.split(':')[1]);
        var end = new Date(y, m, d + (course.day - date.getDay()), course.end_time.split(':')[0], course.end_time.split(':')[1]);
        
        $scope.events.push(
          {title: activity.name, 
           start: start,
           end: end,
           start_text: d + (course.day - date.getDay()),
           end_text: d+  course.day - date.getDay(),
           allDay: false,
           className: $scope.isRegistered(course) ? "registered": "available" ,
           course: course,
           activityId: activity.id
          }
        );
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
        height: 500, aspectRatio: 2,
        year: y, month: m, date: d,
        editable: false,
        defaultView: 'agendaWeek', weekends: false, allDaySlot: false,
        slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 12,
        axisFormat: 'H:mm', columnFormat: 'dddd', header:{left: '', center: '', right: ''},
        dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'], 
        dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
        timeFormat: {agenda: 'd'}, lazyFetching: true,
        eventClick: $scope.eventClick,
        eventAfterRender: function(event, element, view){
          var text = $filter('date')(event.course.start_date, 'shortDate') +' - ' + $filter('date')(event.course.end_date, 'shortDate')
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



var ActivityDetailCtrl = function($scope, $routeParams){
  $scope.activityId = $routeParams.activityId;
  if ($scope.activityId !== undefined) {
    $scope.getDetailedActivity({'id': $scope.activityId});
  }
};