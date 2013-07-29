/* Services */
    
angular.module('sportfacCalendar.services', []).

factory("$store", ["$parse", function($parse){
    'use strict';
    var storage = (typeof window.localStorage === 'undefined') ? undefined : window.localStorage,
        supported = !(typeof storage === 'undefined' || typeof window.JSON === 'undefined');
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
            if (typeof val === 'undefined') { val = res; }
            if (val === 'true') { val = true;}
            if (val === 'false') { val = false;}
            if (parseFloat(val) === val && !angular.isObject(val)) { val = parseFloat(val);}
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
  }])

.factory('Child', function(){
    var Child = function(data){
      angular.extend(this, {
        hasRegistered: function(course){
          return this.registered.indexOf(course.id) !== -1;
        },
        canRegister: function(course){
          return !(this.school_year < course.schoolyear_min || this.school_year > course.schoolyear_max);
        }
      });
      angular.extend(this, data);
      this.registered = [];
    };
    return Child;
  })

.factory('ChildrenService', ["$http", "$cookies", "Child", function($http, $cookies, Child){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    var ModelUtils = {
        all: function(){
          return $http.get('/api/family/').then(function(response){
            var children = [];
            angular.forEach(response.data, function(childData){
              children.push(new Child(childData));
            });
            return children;
          });
        },
        get: function(childId){
          return $http.get('/api/child/' + childId + '/').then(function(response){
            return new Child(response.data);
          });
        }
    };
    
    return ModelUtils;
  }])
  
.factory('Course', function(){
    var date = new Date();
    var d = date.getDate();
    var m = date.getMonth();
    var y = date.getFullYear();

    var Course = function(data){
      angular.extend(this,{
        getStartDate: function(){
          return new Date(y, m, d + (this.day - date.getDay()),
                          this.start_time.split(':')[0],
                          this.start_time.split(':')[1]);},
      
        getEndDate: function(){
          return new Date(y, m, d + (this.day - date.getDay()),
                          this.end_time.split(':')[0],
                          this.end_time.split(':')[1]);},
        
        toEvent: function(className){
          return {title: this.activity.name,
                  start: this.getStartDate(), end: this.getEndDate(),
                  allDay: false,
                  className: className,
                  clickable: className !== 'unavailable',
                  course: this, activityId: this.activity.id};},
        
      });
      angular.extend(this, data);
    };
    return Course;
  })

.factory('CoursesService', ["$http", "$cookies", "Course", function($http, $cookies, Course){
  $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
  var ModelUtils = {
    get: function(courseId){
      return $http.get('/api/courses/' + courseId + '/').then(function(response){
        return new Course(response.data);
      });
    }
  };
  return ModelUtils;
}])

.factory('ModelUtils', ["$http", "$cookies", function($http, $cookies){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    var handleErrors = function(serverResponse, status, errorDestination){
      if (angular.isDefined(errorDestination)){
        angular.forEach(serverResponse, function(value, key){
          errorDestination[key] = value;
        });
      }
    };
        
    var ModelUtils = {
        /*get: function(url, id) {
          $http.get(url + id + '/').
            success(
            function(data, status, headers, config) { return data });
        },*/
        get: function(url, id){
          return $http.get(url + id + '/').then(function(response){
            return response.data;
          });
          
        },
        create: function(url, obj, errors){
          return $http.post(url, obj).
            success(function(response, status, headers, config){
                angular.extend(obj, response);
            }).
            error(function(response, status, headers, config){
                handleErrors(response, status, errors);
            });
        },
        save: function(url, obj, errors){
          if (angular.isDefined(obj.id)){
            return $http.put(url + obj.id + '/', obj).
                     success(function(response, status, headers, config){
                        angular.extend(obj, response);
                     }).
                     error(function(response, status, headers, config){
                       handleErrors(response, status, errors);
                     });
          } else {
            return this.create(url, obj, errors);
          }
        },
        del: function(url, obj){
          return $http.delete(url + obj.id + '/');
        }
    };
    return ModelUtils;
}]);