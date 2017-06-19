

$('#premiumplan').on('click', function(e) {
	// Open Checkout with further options:
	handler.open({
		name: 'Listen Money Matters',
		description: 'Get your questions answered.',
		amount: 5400
	});
	e.preventDefault();
	form = $(this).closest("form")
});

$('#coachingplan').on('click', function(e) {
	// Open Checkout with further options:
	handler.open({
		name: 'Listen Money Matters',
		description: 'Chat with Andrew.',
		amount: 17500
	});
	e.preventDefault();
	form = $(this).closest("form")
});	
	
