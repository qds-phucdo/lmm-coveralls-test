$(document).on('click', '.projections-dropdown li, .invest-dropdown li, .estimation-dropdown li', function(e) {
	$(this).siblings().removeClass('active');
	$(this).addClass('active');
	
	if($(this).closest('.estimation-dropdown').length) {
		$('.estimation-dropdown .dr-btn-text').html($(this).find('a').html());
	}
})

function draw_cash_flow_chart(data, numberOfYear) {
	modifyTableContent(numberOfYear, 'yearly-cf-table');
	var	domEle = 'stacked-bar';
	$('#'+ domEle).html('');	// Clean chart content
	$('.projections-dropdown .dr-btn-text').html(numberOfYear+ ' Years');
	data = data.slice(0, numberOfYear);
	var	stackKey = ["rent","mortgage_payment","property_management","property_taxes","property_insurance"],
		margin = {top: 20, right: 20, bottom: 30, left: 50},
		parseDate = d3.timeParse("%m/%Y"),
		width = $('#' + domEle).width() - margin.left - margin.right,
		height = 400 - margin.top - margin.bottom,
		xScale = d3.scaleBand().range([0, width]).padding(0.2),
		yScale = d3.scaleLinear().range([height, 0]),
		color = ["#6ab358","#d24359","#e8da8d","#7f6ea4","#7bc0d3"],
		xAxis = d3.axisBottom(xScale).tickFormat(d3.timeFormat("%Y")).tickSize(0).tickPadding((-5)),
		yAxis =  d3.axisLeft(yScale).tickSize(-width).tickPadding((5)),
		svg = d3.select("#"+domEle).append("svg")
				.attr("width", width + margin.left + margin.right)
				.attr("height", height + margin.top + margin.bottom)
				.append("g")
				.attr("transform", "translate(" + margin.left + "," + margin.top + ")");

	var stack = d3.stack()
		.keys(stackKey)
		.order(d3.stackOrderNone)
		.offset(d3.stackOffsetNone),
		layers= stack(data);
		
	data.forEach(function(d) {
		var y0_positive = 0;
		var y0_negative = 0;

		d.components = stackKey.map(function(key,i) {
			if (d[key] >= 0) {
				return {key: key, y1: y0_positive, y0: y0_positive += d[key] };
			} else if (d[key] < 0) {
				return {key: key, y0: y0_negative, y1: y0_negative += d[key] };
			}
		})
	});

	xScale.domain(data.map(function(d) { return parseDate(moment(d.date*1000).format("MM/YYYY")); }));
	var y_min = d3.min(data, function(d) {return (d.mortgage_payment+d.property_insurance+d.property_management+d.property_taxes) * 1.1 });
	var y_max = d3.max(data, function(d) { return d.rent });
	yScale.domain([y_min * 1.5, y_max * 1.3]);
	svg.append("g")
		.attr("class", "axis axis--x")
		.attr("transform", "translate(0," + (height+20) + ")")
		.call(xAxis);

	svg.append("g")
	.attr("class", "axis axis--y")
	.attr("transform", "translate(0,0)")
	.attr("transform", "translate(0,0)")
	.call(yAxis);
		
	var layer = svg.selectAll(".layer")
		.data(data)
		.enter().append("g")
		.attr("class", "layer")
		.attr("data-class", function(d, i) {return d.key;})
		.attr("transform", function(d) { return "translate(" + xScale(parseDate(moment(d.date*1000).format("MM/YYYY")))+ ", 0)"; });

	layer.selectAll("rect")
		.data(function(d) {return d.components; })
		.enter().append("rect")
		.attr("class",function(d){return d.key;})
		.style("fill", function(d, i) { return color[i];})
		.attr("y", function(d) { return yScale(d.y0); })
		.attr("height", function(d) {return Math.abs(yScale(d.y0) - yScale(d.y1)); })
		.attr("width", xScale.bandwidth());

	var dataIntermediate =  stackKey.map(function (c) {
		return data.map(function (d,i) {
			return {x:  moment(d.date*1000).format("YYYY") , y: d[c]};
		});
	});
	var dataStackLayout = d3.stack()(dataIntermediate),
		scrubber = svg.append("g")
			.attr("class", "the-scrubber");
	var tooltip = d3.select("#"+domEle)
					.append('div')
					.attr('class', 'tooltip').style("opacity",1);
	svg.append("svg:path")
		.attr("class", "line")
		.attr("stroke", "#000")
		.attr("fill","none")
		.attr("stroke-width","5px");
		
	// Draw net cash flow line
	var line = d3.line()
		.x(function(d) {return xScale(parseDate(moment(d.date*1000).format("MM/YYYY"))); })
		.y(function(d) { return yScale(d.annual_cash_flow);});
	svg.select("path.line").data([data]);
	svg.select("path.line").attr("d", line).attr("transform", "translate("+( xScale.bandwidth()/2)+",0)");	
	
	// Pop up
	var hovertrigger = svg.selectAll(".the-hover-triggers")
			.data(data)
			.enter().append("rect")
			.attr("fill","transparent")
			.attr("x", function (d,i) {return xScale(parseDate(moment(d.date*1000).format("MM/YYYY")));})
			.attr("y", 0)
			.attr("tx", function (d,i) {return xScale(parseDate(moment(d.date*1000).format("MM/YYYY")));})
			.attr("ty", 0)
			.attr("height", height)
			.attr("width",width)
			.on('mouseover',function(d,i){
				if(i < (data.length/2)){
					tooltip.append('div')
					.attr('class', 'mrr-graph__tooltip')
					.attr('style','position:absolute;opacity:1;top:'+(yScale(d.annual_cash_flow)-300)+'px;left:'+(xScale(parseDate(moment(d.date*1000).format("MM/YYYY")))+235)+'px;')
					.html(function() {
						html = "<div class='current'>"+moment(d.date*1000).format("MMMM YYYY")+"</div>";
						html += '<div class="col-table"><div class="col names">';
						html += '<span class="contract">Rental Income</span>'
						html += '<span class="react">Mortgage Payment</span>'
						html += '<span class="exp">Property Management</span>'
						html += '<span class="new">Property Taxes</span>'
						html += '<span class="churn">Property Insurance</span>'
						html += '<span class="net">Net Cash Flow</span>'
						html += '</div>';
						html += '<div class="col amounts">'
						html += '<span class="contract">$'+ data[i].rent.format(2) +'</span>'
						html += '<span class="react">$'+ data[i].mortgage_payment.format(2) +'</span>'
						html += '<span class="exp">$'+ data[i].property_management.format(2) +'</span>'
						html += '<span class="new">$'+ data[i].property_taxes.format(2) +'</span>'
						html += '<span class="churn">$'+ data[i].property_insurance.format(2) +'</span>'
						html += '<span class="net">$'+ data[i].annual_cash_flow.format(2) +'</span>'
						html += '</div>';
						return html;
					});
				}else{
					tooltip.append('div')
					.attr('class', 'mrr-graph__tooltip')
					.attr('style','position:absolute;opacity:1;top:'+(yScale(d.annual_cash_flow)-300)+'px;left:'+(xScale(parseDate(moment(d.date*1000).format("MM/YYYY")))-105)+'px;')
					.html(function() {
						html = "<div class='current'>"+moment(d.date*1000).format("MMMM YYYY")+"</div>";
						html += '<div class="col-table"><div class="col names">';
						html += '<span class="contract">Rental Income</span>'
						html += '<span class="react">Mortgage Payment</span>'
						html += '<span class="exp">Property Management</span>'
						html += '<span class="new">Property Taxes</span>'
						html += '<span class="churn">Property Insurance</span>'
						html += '<span class="net">Net Cash Flow</span>'
						html += '</div>';
						html += '<div class="col amounts">'
						html += '<span class="contract">$'+ data[i].rent.format(2) +'</span>'
						html += '<span class="react">$'+ data[i].mortgage_payment.format(2) +'</span>'
						html += '<span class="exp">$'+ data[i].property_management.format(2) +'</span>'
						html += '<span class="new">$'+ data[i].property_taxes.format(2) +'</span>'
						html += '<span class="churn">$'+ data[i].property_insurance.format(2) +'</span>'
						html += '<span class="net">$'+ data[i].annual_cash_flow.format(2) +'</span>'
						html += '</div>';
						return html;
					});
				}
				
				scrubber.append('rect')
					.attr('x',function () {
						return (xScale(parseDate(moment(d.date*1000).format("MM/YYYY")))+xScale.bandwidth()/2);
					})
					.attr('y',-25)
					.attr('width',2)
					.attr('height',height+25)
					.attr('fill',"white");

				scrubber.append('circle')
					.data([data])
					.attr('cx',function () {
						return (xScale(parseDate(moment(d.date*1000).format("MM/YYYY")))+xScale.bandwidth()/2);
					})
					.attr('cy',function (e) {
						return (yScale(e[i].annual_cash_flow))
					})
					.attr('r',8)
					.attr('fill',"#000");
					
				$("#yearly-cf-table .breakout-scroller .column:eq("+ (i) +")").addClass("active");
			})
			.on('mouseout', function(d,i){
				scrubber.html("");
				d3.select("#"+ domEle +" .tooltip").html("");
				$("#yearly-cf-table .breakout-scroller .column").removeClass('active');
			})
			.on('click',function(d,i){	// Scroll Table follow graph after click event
				$("#yearly-cf-table .breakout-scroller").animate({
					scrollLeft: $("#yearly-cf-table .breakout-scroller .column").last().width() * ((i+1) - 4)
				}, 250)
				
				$("#yearly-cf-table .breakout-scroller .column:eq("+ (i) +")").addClass("active");
			});

	layer.selectAll("rect")
		.data(function (d) {
			return d;
		})
		.enter().append("rect")
		.attr("x", function (d) {
			return x(d.x);
		})
		.attr("y", function (d) {
			return y(d.y );
		})
		.attr("height", function (d) {
			return y(d.y0) - y(d.y );
		})
		.attr("width", xScale.bandwidth());
		
	$('#yearly-cf-table .breakout').removeClass('hidden');
}

function modifyTableContent(numberOfYear, tableId) {
	$("#"+ tableId +" .breakout-scroller .column").removeClass('hidden');
	$("#"+ tableId +" .breakout-scroller .column:gt("+ (numberOfYear - 1) +")").addClass("hidden");
	if(tableId == 'yearly-equity-table') {
		$('#yearly-equity-table .column .cf').addClass('hidden');
		$('#yearly-equity-table .column .total').addClass('hidden');
		$('#yearly-equity-table .column .cf.'+ cashflow_style).removeClass('hidden');
		$('#yearly-equity-table .column .total.total_'+ cashflow_style).removeClass('hidden');
	}
}

function drawYearlyEquity(dataRaw, numberOfYear) {
	modifyTableContent(numberOfYear, 'yearly-equity-table');
	$('#yearly-equity').html('');	// Clean chart content
	$('.invest-dropdown .dr-btn-text').html(numberOfYear+ ' Years');
	
	var margin = {
			top: 20,
			right: 20,
			bottom: 30,
			left: 50
		},
		width = $('#yearly-equity').width() - margin.left - margin.right,
		height = 400 - margin.top - margin.bottom,
		x = d3.scaleLinear().range([0, width]),
		y = d3.scaleLinear().range([height, 0]);
		color = d3.scaleOrdinal(["#6AB358","#7bc0d3","#7f6ea4"]),
		xAxis = d3.axisBottom(x).ticks(numberOfYear <= 3 ? numberOfYear-1 : numberOfYear).tickFormat(d3.format("")),
		yAxis = d3.axisLeft(y).tickSize(-width),
		equityMaxValue = 0,
		appreciationMaxValue = 0,
		cashflowMaxValue = 0;

	// format the data
	var cloneArray = JSON.parse(JSON.stringify(dataRaw));
	var data = cloneArray.slice(0, numberOfYear);
	data.forEach(function(d) {
		d.dateTimestamp = d.date;
		d.date = typeof(d.date) == 'string' ? d.date : moment(d.date*1000).format("YYYY");
		equityMaxValue = d.equity > equityMaxValue ? d.equity : equityMaxValue;
		appreciationMaxValue = d.appreciation > appreciationMaxValue ? d.appreciation : appreciationMaxValue;
		cashflowMaxValue = d[cashflow_style] > cashflowMaxValue ? d[cashflow_style] : cashflowMaxValue;
	});
	var yScaleMax = equityMaxValue + appreciationMaxValue + cashflowMaxValue;
	
	y.domain([d3.min(data, function(d) {return Math.min(d[cashflow_style],d.appreciation,d.equity); }) > 0 ? 0 :d3.min(data, function(d) {return Math.min(d[cashflow_style],d.appreciation,d.equity); }), (yScaleMax) * 1.1]);
	x.domain(d3.extent(data, function(d) {return d.date;}));
	var stack = d3.stack(),
		area = d3.area()
				.x(function(d,i) {
				    return x(d.date);
				})
				.y0(function(d) {
				    return y(d.y0);
				})
				.y1(function(d,i) {
				    if (d.name == 'appreciation') {
				        return y(d.y + browsers[2].values[i].y);
				    } else if(d.name == cashflow_style) {
				        return y(d.y + browsers[1].values[i].y + browsers[2].values[i].y);
				    } else {
				        return y(d.y);
				    }
				});
	var svg = d3.select("#yearly-equity").append("svg")
		.attr("width", width + margin.left + margin.right)
		.attr("height", height + margin.top + margin.bottom)
		.append("g")
		.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
	color.domain([cashflow_style, "appreciation", "equity"]);
	svg.append("g")
	    .attr("class", "x axis")
	    .attr("transform", "translate(0," + height + ")")
	    .call(xAxis);
	svg.append("g")
	    .attr("class", "y axis")
	    .call(yAxis);
	var browsers = color.domain().map(function(name) {
		return {
			name: name,
			values: data.map(function(d) {
				return {
					date: d.date,
					y: d[name],
					y0:0,
					name: name
				};
			})
		};
	});
	var vars = svg.selectAll(".vars")
		.data(browsers)
		.enter().append("g")
		.attr("class", "vars");
	
	vars.append("path")
		.attr("class", function(d) {
			return (d.name);
		})
		.attr("d", function(d) {
			return area(d.values);
		})
		.style("fill", function(d) {
			return color(d.name);
		});
	var scrubber = svg.append("g")
		.attr("class", "the-scrubber");
	var tooltip = d3.select("#yearly-equity").append('div')
		.attr('class', 'tooltip');
	svg.append("g")
		.attr("class","rect")
		.selectAll(".rect")
		.data(browsers[0].values)
		.enter()
		.append("rect")
		.style("fill-opacity", 0)
		.attr("y",0)
		.attr("x",function(d) {
		    return x(d.date);
		})
		.attr("width",width + margin.left + margin.right)
		.attr("height",height + margin.top + margin.bottom)
		.on("mouseover", function(e,i) {
			$('#yearly-equity .tooltip').css({'opacity': '1', 'position': 'initial'});
		    if(i < (data.length/2)){
		        tooltip.append('div')
		        .attr('class','mrr-graph__tooltip')
		        .attr('style','position:absolute;opacity:1;top:'+(y(data[i][cashflow_style]))+'px;left:'+(x(data[i].date)+250)+'px;')
		        .html(function() {
		            html = "<div class='current'>"+ moment(data[i].dateTimestamp * 1000).format('YYYY-MM-DD') +"</div>";
		            html += '<div class="col-table"><div class="col names">';
		            html += '<span class="cashflow">Cash flow</span>'
		            html += '<span class="appreciation">Appreciation</span>'
		            html += '<span class="equity">Equity</span>'
		            html += '<span class="total">Total Value</span>'
		            html += '</div>';
		            html += '<div class="col amounts">'
		            html += '<span class="cashflow">$'+ data[i][cashflow_style].format(2) +'</span>'
		            html += '<span class="appreciation">$'+ data[i].appreciation.format(2) +'</span>'
		            html += '<span class="equity">$'+ data[i].equity.format(2) +'</span>'
		            html += '<span class="total">$'+ data[i]['total_'+ cashflow_style].format(2) +'</span>'
		            html += '</div>';
		            return html;
		        });
		    }else{
		        tooltip.append('div')
		        .attr('class', 'mrr-graph__tooltip')
		        .attr('style','position:absolute;opacity:1;top:'+(y(data[i].equity))+'px;left:'+(x(data[i].date)-120)+'px;')
		        .html(function() {
		            html = "<div class='current'>"+ moment(data[i].dateTimestamp * 1000).format('YYYY-MM-DD') +"</div>";
		            html += '<div class="col-table"><div class="col names">';
		            html += '<span class="cashflow">Cash flow</span>'
		            html += '<span class="appreciation">Appreciation</span>'
		            html += '<span class="equity">Equity</span>'
		            html += '<span class="total">Total Value</span>'
		            html += '</div>';
		            html += '<div class="col amounts">'
		            html += '<span class="cashflow">$'+ data[i][cashflow_style].format(2) +'</span>'
		            html += '<span class="appreciation">$'+ data[i].appreciation.format(2) +'</span>'
		            html += '<span class="equity">$'+ data[i].equity.format(2) +'</span>'
		            html += '<span class="total">$'+ data[i]['total_'+ cashflow_style].format(2) +'</span>'
		            html += '</div>';
		            return html;
		        });
		    }
		
		    scrubber.append('rect')
		        .attr('x',function () {
		            return (x(data[i].date));})
		        .attr('y',0)
		        .attr('width',2)
		        .attr('height',height)
		        .attr('fill',"white");
		
		    scrubber.append('circle')
		        .data([data])
		        .attr('cx',function () {
		            return x(data[i].date) + 0.6;})
		        .attr('cy',function () {
		            return y(data[i][cashflow_style] + data[i].equity + data[i].appreciation);})
		        .attr('r',5)
		        .attr('fill',color("cashflow"))
		        .attr('class',"cashflow");
		
		    scrubber.append('circle')
		        .data([data])
		        .attr('cx',function () {
		            return x(data[i].date) + 0.6;})
		        .attr('cy',function () {
		            return y(data[i].appreciation + data[i].equity);})
		        .attr('r',5)
		        .attr('fill',color("appreciation"))
		        .attr('class',"appreciation");
		
		    scrubber.append('circle')
		        .data([data])
		        .attr('cx',function () {
		           return x(data[i].date) + 0.8;})
		        .attr('cy',function () {
		           return y(data[i].equity);})
		        .attr('r',5)
		        .attr('fill',color("equity"))
		        .attr('class',"equity");
		        
			$("#yearly-equity-table .breakout-scroller .column:eq("+ (i) +")").addClass("active");
		})
		.on("mouseout", function(e,i) { 
		    scrubber.html("");
		    d3.select("#yearly-equity .tooltip").html("");
		    $("#yearly-equity-table .breakout-scroller .column").removeClass('active');
		})
		.on('click',function(d,i){	// Scroll Table follow graph after click event
			$("#yearly-equity-table .breakout-scroller").animate({
				scrollLeft: $("#yearly-equity-table .breakout-scroller .column").last().width() * ((i+1) - 4)
			}, 250)
			
			$("#yearly-equity-table .breakout-scroller .column:eq("+ (i) +")").addClass("active");
		});
		
	$('#yearly-equity-table .breakout').removeClass('hidden');
	$('#projections-page').css('opacity', '1');
}

function changeCashflowStyle(selected) {
	cashflow_style = selected;
	var numberOfyear = $('.invest-dropdown li.active').attr('data-value');
	drawYearlyEquity(equity_chart, parseInt(numberOfyear));
}

function changeProjectionsAssumptions() {
	var post_data = {
		address: property_address,
		rent_growth: +$('#lblrentgrowth').text() / 100,
		apprection_percent: +$('#lblappreciation').text()  / 100,
		tax_increase: +$('#lbltaxincrease').text()  / 100,
		insurance_increase: +$('#lblinsuranceincrease').text() / 100,
	};

	$.ajax({
		url: '/_get_projections_ajax',
		type: 'POST',
		contentType: 'application/json',
		data: JSON.stringify(post_data),
		success: function(response) {
			var results = JSON.parse(response);
			if(results.status == 'OK') {
				// Change tables content
				$('#yearly-cf-table').html(results.projections_table);
				$('#yearly-equity-table').html(results.yearly_equity_table);

				// Reset variables and draw charts
				projections_chart = results.projections;
				equity_chart = results.yearly_equity;
				draw_cash_flow_chart(projections_chart, parseInt($('.projections-dropdown li.active').attr('data-value')));
				drawYearlyEquity(equity_chart, parseInt($('.invest-dropdown li.active').attr('data-value')));
			}
		},
		error: function(error) {
			console.log(error);
		}
	});
	
	// Format value display
	$('#lblrentgrowth').text((+$('#lblrentgrowth').text()).format(2));
	$('#lblappreciation').text((+$('#lblappreciation').text()).format(2));
	$('#lbltaxincrease').text((+$('#lbltaxincrease').text()).format(2));
	$('#lblinsuranceincrease').text((+$('#lblinsuranceincrease').text()).format(2));
	$('#lblrentgrowth').next('input').val((+$('#lblrentgrowth').text()).format(2));
	$('#lblappreciation').next('input').val((+$('#lblappreciation').text()).format(2));
	$('#lbltaxincrease').next('input').val((+$('#lbltaxincrease').text()).format(2));
	$('#lblinsuranceincrease').next('input').val((+$('#lblinsuranceincrease').text()).format(2));
}

var projections_chart = JSON.parse('{{ projections }}');
var equity_chart = JSON.parse('{{ yearly_equity }}');
var cashflow_style = "cashflow";
var property_address = "{{ p.address }}";
draw_cash_flow_chart(projections_chart, 30);
drawYearlyEquity(equity_chart, 30);
