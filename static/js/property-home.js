var initSearchField = function () {
	$('.navbar-search-field').focus (function (e) {
		$(this).parents ('form').addClass ('active')
		$(this).animate ({ width: '250px' })
	}).blur (function (e) {	
		$(this).parents ('form').removeClass ('active')
			
		if (!$(this).val ()) {
			$(this).animate ({ width: '270px' })
		}
	})
};

initSearchField();
