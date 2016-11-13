/* Services */
    
angular.module('sportfacCalendar.services', []).

factory('Registration', function(){
    var Registration = function(data){
      /*angular.extend(this, {
        delete: function(course){
          return this.registered.indexOf(course.id) !== -1;
        },
        canRegister: function(course){
          return !(this.school_year < course.schoolyear_min || this.school_year > course.schoolyear_max);
        }
      });*/
      
      angular.extend(this, data);
    };
    return Registration;
  })

.factory('RegistrationsService', ["$http", "$cookies", "Registration", function($http, $cookies, Registration){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    var handleErrors = function(serverResponse, status, errorDestination){
      if (angular.isDefined(errorDestination)){
        angular.forEach(serverResponse, function(value, key){
          errorDestination[key] = value;
        });
      }
    };

    var ModelUtils = {
        all: function(url){
          return $http.get(url).then(function(response){
            var registrations = [];
            angular.forEach(response.data, function(registrationData){
              registrations.push(new Registration(registrationData));
            });
            return registrations;
          });
        },
        get: function(url, registrationId){
          return $http.get(url + registrationId + '/').then(function(response){
            return new Registration(response.data);
          });
        },
        del: function(url, obj){
          return $http.delete(url + obj.id + '/');
        },
        create: function(url, obj, errors){
          return $http.post(url, obj).
            success(function(response){
                angular.extend(obj, response);
            }).
            error(function(response, status){
                handleErrors(response, status, errors);
            });
        },
        save: function(url, obj, errors){
          if (angular.isDefined(obj.id)){
            return $http.put(url + obj.id + '/', obj).
                     success(function(response){
                        angular.extend(obj, response);
                     }).
                     error(function(response, status){
                       handleErrors(response, status, errors);
                     });
          } else {
            return this.create(url, obj, errors);
          }
        }
    };
    
    return ModelUtils;
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
        all: function(url){
          return $http.get(url).then(function(response){
            var children = [];
            angular.forEach(response.data, function(childData){
              children.push(new Child(childData));
            });
            return children;
          });
        },
        get: function(url, childId){
          return $http.get(url + childId + '/').then(function(response){
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
                  course: this, activityId: this.activity.id};}
        
      });
      angular.extend(this, data);
    };
    return Course;
  })

.factory('CoursesService', ["$http", "$cookies", "Course", function($http, $cookies, Course){
  $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
  var ModelUtils = {
    get: function(url, courseId){
      return $http.get(url + courseId + '/').then(function(response){
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
            success(function(response){
                angular.extend(obj, response);
            }).
            error(function(response, status){
                handleErrors(response, status, errors);
            });
        },
        save: function(url, obj, errors){
          if (angular.isDefined(obj.id)){
            return $http.put(url + obj.id + '/', obj).
                     success(function(response){
                        angular.extend(obj, response);
                     }).
                     error(function(response, status){
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