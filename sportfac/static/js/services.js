//'use strict';

/* Services */
    
angular.module('sportfac.services', []).
  value('version', '0.1').
  value('localStorage', window.localStorage).
  service('calendars', function (localStorage, $rootScope) {

    

    var self = this;
  
    self.getCourses = function(child){
      if (!(self.calendars.hasOwnProperty(child.id))){
        self.calendars[child.id] = Array();
      }
      return self.calendars[child.id];
    }
  
    self.addCourse = function(child, course) {
      if (!(self.calendars.hasOwnProperty(child.id))){
        self.calendars[child.id] = Array();
      }
      self.calendars[child.id].push(course);
    };
    
    
    self.reset = function(){
      self.calendars = {};
    };

    
      
    
    createPersistentProperty('calendars', 'sportfacCalendars', Object);
    
    function createPersistentProperty(localName, storageName, Type) {
      var json = localStorage[storageName];
      self[localName] = json ? JSON.parse(json) : new Type;
      
      $rootScope.$watch(
        function () { return self[localName];},
        function (value) { if (value) { localStorage[storageName] = JSON.stringify(value); }},
        true);
    }

    

  });
