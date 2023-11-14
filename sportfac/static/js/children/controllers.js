angular.module('sportfacChildren.controllers', [])

.controller('ListCtrl', ["$scope", "$attrs", "$routeParams", "$http", "ChildrenService",
function($scope, $attrs, $routeParams, $http, ChildrenService) {
  'use strict';
  if (!$attrs.prefill) throw new Error("No prefill option set");
  $scope.prefillTeachers = $attrs.prefill === 'true';
  if (!$attrs.external) throw new Error("No external option set");
  $scope.useExternalIdentifiers = $attrs.external === 'true';
  if (!$attrs.buildings) throw new Error("No building option set");
  $scope.useBuildings = $attrs.buildings === 'true';
  if (!$attrs.schools){
      $scope.schools = [];
  } else {
      $scope.schools = angular.fromJson($attrs.schools);
  }
  $scope.urls = {
    child: $attrs.childserviceurl,
    building: $attrs.buildingserviceurl,
    teacher: $attrs.teacherserviceurl,
    year: $attrs.yearserviceurl
  };
  $scope.routeParams = $routeParams;
  $scope.loadChildren = function(){
    ChildrenService.all($scope.urls.child).then(function(children){

      $scope.userChildren = children;
      angular.forEach(children, function(child){
        if (child.id === parseInt($scope.routeParams.childId, 10)) {
            child.selected = true;
            $scope.selectedChild = child;
        } else {
            child.selected = false;
        }
      });
    });
  };

  $scope.loadTeachers = function(){
    $http.get($scope.urls.teacher).success(function(data, status, headers, config ){
        $scope.teachers = data;
    });
  };

  $scope.loadBuildings = function(){
    $http.get($scope.urls.building).success(function(data, status, headers, config ){
        $scope.buildings = data;
    });
  };

  $scope.loadYears = function(){
    $http.get($scope.urls.year).success(function(data, status, headers, config ){
        $scope.years = data;
    });
  };

  $scope.teachers = [];
  if ($scope.prefillTeachers){
    $scope.loadTeachers();
    if ($scope.useBuildings){
      $scope.loadBuildings();
    }
  } else {
    $scope.loadYears();
  }
  $scope.loadChildren();

  $scope.selectChild = function(child){
    if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = child;
    $scope.selectedChild.selected = true;
  };
  $scope.unselectChild = function(){
     if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = undefined;
  };
}])

.controller('childDetailCtrl', ["$scope", "$routeParams", "$location", "ChildrenService",
  function($scope, $routeParams, $location, ChildrenService) {
  'use strict';
  $scope.detailedChild = {};
  this.initialValue = {};
  $scope.errors = {};
  $scope.availableTeachers = $scope.teachers.slice();

  $scope.reloadChild = function(){
    ChildrenService.get($scope.urls.child, $routeParams.childId).then(function(child){
      for (var i=0; i< $scope.teachers.length; i++){
        var teacher = $scope.teachers[i];
        if (teacher.id === child.teacher){
          child.teacher = teacher;
          break;
        }
      }
      $scope.detailedChild = child;
      $scope.initialValue = angular.copy(child);
    });
  };
  $scope.reloadChild();

  $scope.updateSchoolYear = function(){
    $scope.detailedChild.school_year = $scope.detailedChild.teacher.years[0];
  };

  $scope.updateTeachers = function(){
    $scope.availableTeachers = $scope.teachers.filter(function(teacher) {
        return teacher.buildings.includes($scope.detailedChild.building.id);
    });
  };

  $scope.saveChild = function(){
    ChildrenService.save($scope.urls.child, $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };

  $scope.delChild = function(){
     ChildrenService.del($scope.urls.child, $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };

  $scope.resetForm = function(){
      $scope.detailedChild = {};
  };

  $scope.hasNotChanged = function() {
    return angular.equals(this.initialValue, $scope.detailedChild);
  };
}])

.controller('childAddCtrl', ["$scope", "$location", "ChildrenService",
function($scope, $location, ChildrenService) {
  $scope.unselectChild();
  if ($scope.schools.length){
      $scope.detailedChild = {school: $scope.schools[0].id, sex: 'F'};
  } else {
      $scope.detailedChild = {sex: 'F'};
  }

  $scope.errors = {notfound: false};
  $scope.resetForm = function(){
    $scope.detailedChild = {};
  };
  $scope.updateSchoolYear = function(){
    $scope.detailedChild.school_year = $scope.detailedChild.teacher.years[0];
  };

  $scope.lookupChild = function(){
    ChildrenService.lookup($scope.urls.child, $scope.detailedChild.ext_id, $scope.errors).then(function(child){
      if (child !== undefined) {
        for (var i=0; i< $scope.teachers.length; i++){
          var teacher = $scope.teachers[i];
          if (teacher.id === child.teacher){
            child.teacher = teacher;
            break;
          }
        }
        $scope.detailedChild = child;
      } else {
        $scope.detailedChild.ext_id = '';
      }

    });
  };

  $scope.saveChild = function(){
    ChildrenService.save($scope.urls.child, $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $scope.detailedChild = {};
      $location.url('/new');
    });
  };
}]);
