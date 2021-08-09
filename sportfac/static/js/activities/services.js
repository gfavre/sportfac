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
        canRegister: function(course, limitbyschoolyear){
          if (limitbyschoolyear) {
            return !(this.school_year < course.schoolyear_min || this.school_year > course.schoolyear_max);
          } else {
            return course.min_birth_date >= this.birth_date;
          }
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
      angular.extend(this, {
        getStartDate: function(){
          var course = this;
          if (this.course_type == 'course') {
            return new Date(y, m, d + (this.day - date.getDay()),
                          course.start_time.split(':')[0],
                          course.start_time.split(':')[1]);
          } else {
            var startDate = new Date(course.start_date);
            return new Date(y, m, d + startDate.getDay() - date.getDay());
          }
        },
        getEndDate: function(){
          if (this.course_type == 'course') {
            return new Date(y, m, d + (this.day - date.getDay()),
              this.end_time.split(':')[0],
              this.end_time.split(':')[1]);
          } else {
            var endDate = new Date(this.end_date);
            return new Date(y, m, d + endDate.getDay() - date.getDay());
          }
        },
        toEvents: function(className) {
          var course = this;
          var genEvent = function (days, startTime, endTime) {
            var start = course.getStartDate();
            start.setDate(start.getDate() + days)
            if (startTime !== null) {
              start.setHours(startTime.split(':')[0])
              start.setMinutes(startTime.split(':')[1])
            }
            if (course.course_type == 'multicourse') {
              var end = new Date(start.getTime());
              var eventId = course.id + '-' + days;
              var groupId = course.id;
            } else {
              var end = course.getEndDate();
              var eventId = course.id;
              var groupId = course.id;

            }
            if (endTime !== null) {
              end.setHours(endTime.split(':')[0])
              end.setMinutes(endTime.split(':')[1])
            }
            return {
              id: eventId,
              groupId: groupId,
              title: course.activity.name,
              start: start, end: end,
              allDay: false,
              className: className,
              clickable: className !== 'unavailable',
              course: course, activityId: course.activity.id
            };
          };

          if (this.course_type != 'multicourse') {
            return [genEvent(0, this.start_time, this.end_time)];
          } else {
            var output = [];
            if (this.multi_course.start_time_mon !== null) {
              output.push(genEvent(0, this.multi_course.start_time_mon, this.multi_course.end_time_mon))
            }
            if (this.multi_course.start_time_tue !== null) {
              output.push(genEvent(1, this.multi_course.start_time_tue, this.multi_course.end_time_tue))
            }
            if (this.multi_course.start_time_wed !== null) {
              output.push(genEvent(2, this.multi_course.start_time_wed, this.multi_course.end_time_wed))
            }
            if (this.multi_course.start_time_thu !== null) {
              output.push(genEvent(3, this.multi_course.start_time_thu, this.multi_course.end_time_thu))
            }
            if (this.multi_course.start_time_fri !== null) {
              output.push(genEvent(4, this.multi_course.start_time_fri, this.multi_course.end_time_fri))
            }
            if (this.multi_course.start_time_sat !== null) {
              output.push(genEvent(5, this.multi_course.start_time_sat, this.multi_course.end_time_sat))
            }
            if (this.multi_course.start_time_sun !== null) {
              output.push(genEvent(6, this.multi_course.start_time_sun, this.multi_course.end_time_sun))
            }
            return output;
          }
        }
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