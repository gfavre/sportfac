'use strict';
if (!Array.prototype.indexOf) {
  Array.prototype.indexOf = function (obj, fromIndex) {
    if (fromIndex == null) {
        fromIndex = 0;
    } else if (fromIndex < 0) {
        fromIndex = Math.max(0, this.length + fromIndex);
    }
    for (var i = fromIndex, j = this.length; i < j; i++) {
        if (this[i] === obj)
            return i;
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
                  publicMethods.set(key, Array());
              }
              $scope[key] = publicMethods.get(key);
              
              /*$scope.$watch(key, function (val) {
                  publicMethods.set(key, val);
              }, true);*/
              $scope.$watchCollection(key, function(newElems, oldElems){
                 alert('save!');
                 publicMethods.set(key, newElems); 
              });
              
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
      $scope.selectChild(0);
    });
  };
  $scope.selectChild = function(childIdx){
    if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = $scope.userChildren[childIdx];
    $scope.selectedChild.selected = true;
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
  
  $scope.getUserChildren();
  $store.bind($scope, 'registeredEvents');
  
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

var ActivityTimelineCtrl = function($scope, $routeParams, $filter, $store){    
    // this controler is reloaded each time an activity is changed
    $scope.events = [];
    $scope.eventSources = [$scope.events, $scope.registeredEvents];
    
    var date = new Date();
    var d = date.getDate();
    var m = date.getMonth();
    var y = date.getFullYear();
    
    
    $scope.changeActivity = function(activity){
      $scope.events.length = 0;
      
      for (var i=0; i<activity.courses.length; i++){
        var course = activity.courses[i];
        if (course.schoolyear_min > $scope.selectedChild.school_year || course.schoolyear_max < $scope.selectedChild.school_year) continue;
        var start = new Date(y, m, d + (course.day - date.getDay()), course.start_time.split(':')[0], course.start_time.split(':')[1]);
        var end = new Date(y, m, d + (course.day - date.getDay()), course.end_time.split(':')[0], course.end_time.split(':')[1]);
        
        $scope.events.push(
          {title: activity.name + ' \n ' + $filter('date')(course.start_date, 'mediumDate') +' - ' + $filter('date')(course.end_date, 'mediumDate'), 
           start: start,
           end: end,
           start_text: d + (course.day - date.getDay()),
           end_text: d+  course.day - date.getDay(),
           allDay: false,
           color: "#0088cc",
           course: course}
        );
      }
    };
    
    $scope.eventClick = function( calEvent, jsEvent, view ){
      calEvent.color = 'green';    
      $scope.registeredEvents.push(calEvent);      
      $scope.weekagenda.fullCalendar('updateEvent', calEvent);
    };
    
    $scope.uiConfig = {
      calendar:{
        height: 500, aspectRatio: 4,
        year: y, month: m, date: d,
        editable: false,
        defaultView: 'agendaWeek',
        weekends: false, allDaySlot: false,
        slotMinutes: 15, firstHour: 12, maxTime: 20, minTime: 12,
        axisFormat: 'H:mm', columnFormat: 'dddd d',
        dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
        dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
        header:{left: '', center: '', right: ''},
        eventClick: $scope.eventClick,//function(){$scope.$apply($scope.eventClick)},
        timeFormat: {agenda: ''},
        lazyFetching: true
      }
    };
 
    $scope.getDetailedActivity($routeParams.activityId, 
                               function(detailedActivity){
                                 $scope.detailedActivity = detailedActivity;
                                 $scope.changeActivity(detailedActivity);
                                 // rechargmenent F5
                                 $scope.weekagenda.fullCalendar('render');
                                 // reclic sur la barre
                                 $scope.weekagenda.fullCalendar('refetchEvents');
                               });
    


}

var ActivityDetailCtrl = function($scope, $routeParams){
  $scope.activityId = $routeParams.activityId;
  //$scope.activityId = 3;
  if ($scope.activityId != undefined) {
    $scope.getDetailedActivity({'id': $scope.activityId});
  }
}
//ActivityDetailCtrl.$inject = ['$scope', '$routeParams'];
  
