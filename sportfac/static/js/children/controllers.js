angular.module('sportfacChildren.controllers', [])

.controller('ListCtrl', ["$scope", "$attrs", "$routeParams", "$http", "ChildrenService",
function($scope, $attrs, $routeParams, $http, ChildrenService) {
  'use strict';
  if (!$attrs.prefill) throw new Error("No prefill option set");
  $scope.prefillTeachers = $attrs.prefill === 'true';
  if (!$attrs.external) throw new Error("No external option set");
  $scope.useExternalIdentifiers = $attrs.external === 'true';
  if (!$attrs.schools){
      $scope.schools = [];
  } else {
      $scope.schools = angular.fromJson($attrs.schools);
  }
  $scope.urls = {
    child: $attrs.childserviceurl,
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

  $scope.loadYears = function(){
    $http.get($scope.urls.year).success(function(data, status, headers, config ){
        $scope.years = data.map(function(year){ return year.year; });
    });
  };
  
  $scope.teachers = [];
  if ($scope.prefillTeachers){
    $scope.loadTeachers();
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
  
  $scope.toHarmos = function(year) {
    return {1: "1P",
            2: "2P",
            3: "3P",
            4: "4P",
            5: "5P",
            6: "6P",
            7: "7P",
            8: "8P",
            9: "9S",
            10: "10S",
            11: "11S",
            12: "12R"}[year];
    
  };
}])

.controller('childDetailCtrl', ["$scope", "$routeParams", "$location", "ChildrenService",
  function($scope, $routeParams, $location, ChildrenService) {
  'use strict';
  console.log('$attrs');
  $scope.detailedChild = {};
  this.initialValue = {};
  $scope.errors = {};
  
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
  
  
  $scope.saveChild = function(){
    ChildrenService.save($scope.urls.child, $scope.detailedChild).then(function(){
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
      $scope.detailedChild = {school: $scope.schools[0].id};
  } else {
      $scope.detailedChild = {};
  }
  
  $scope.errors = {};
  $scope.resetForm = function(){
    $scope.detailedChild = {};
  };
  $scope.updateSchoolYear = function(){
    $scope.detailedChild.school_year = $scope.detailedChild.teacher.years[0];
  };
  
  $scope.lookupChild = function(){
    ChildrenService.lookup($scope.urls.child, $scope.detailedChild.ext_id).then(function(child){
      for (var i=0; i< $scope.teachers.length; i++){
        var teacher = $scope.teachers[i];
        if (teacher.id === child.teacher){
          child.teacher = teacher;
          break;
        }
      }
      $scope.detailedChild = child;
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