

// Declare app level module which depends on filters, and services
angular.module('children', [ 'children.services' ]).
  config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/edit', {templateUrl: '/static/partials/child-detail.html', controller: 'childDetailCtrl'});
    $routeProvider.otherwise({redirectTo: '/view1'});
  }]).
  config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[{');
    $interpolateProvider.endSymbol('}]}');
});



var ListCtrl = function ($scope, $http) {
  $scope.getUserChildren = function(){
    $http.get('/api/family/').success(function(data){ 
      $scope.userChildren = data;
    });
  };
  $scope.selectChild = function(child){
    if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = child;
    $scope.selectedChild.selected = true;
  };

  $scope.userChildren = [];
  $scope.selectedChild = {};
  $scope.getUserChildren();
};


var childDetailCtrl = function ($scope, Child) {
  var Child = $resource('/api/family/:childId',{childId:'@id'});
  var cc = Child.query(function(){
    alert(cc[0]);
  });
  
  var newChild = new Child({first_name: 'Maurice'});
  newChild.$save();
  
  
  /*$scope.otherChild = Children.get({childId: 2}, function(){
    //otherChild.firstName='Maurice';
    //otherChild.$save();
    
  });*/
};