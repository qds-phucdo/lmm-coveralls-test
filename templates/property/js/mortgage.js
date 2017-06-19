$(function () {
	//var d1, d2, d3, data, chartOptions
	
	/*
	equity = [
		{{ p.calc.chart_equity_value }}
	]
	
	loan_balance = [
		{{ p.calc.chart_loan_balance }}
	]
	
	property_value = [
		{{ p.calc.chart_property_value }}
	]
	
	
	data = [{
		label: "Property Value",
		data: property_value
	}, {
		label: "Equity", 
		data: equity
	}, {
		label: "Loan Balance",
		data: loan_balance
	}]
	

	var chartOptions = {
		xaxis: {
			min: {{ p.calc.mortgage_start|replace(",", "") }},
			max: {{ p.calc.mortgage_end|replace(",", "") }},
			mode: "time",
			timeformat: "%S",
			minTickSize: [3, "year"]
		},
		yaxis: {
		
		},
		series: {
			stack: true,
			lines: {
				show: true, 
				fill: true,
				lineWidth: 3
			},
			points: {
				show: false,
				radius: 4.5,
				fill: true,
				fillColor: "#ffffff",
				lineWidth: 2.75
			}
		},
		grid: { 
			hoverable: true, 
			clickable: false, 
			borderWidth: 0 
		},
		legend: {
			show: true
		},
			tooltip: true,
			tooltipOpts: {
			content: '%s: %y'
		},
		colors: ['#6685a4', '#5cb85c', '#d74b4b']
	}

	var holder = $('#stacked-area-chart')
	
	if (holder.length) {
		$.plot(holder, data, chartOptions )
	}
	*/
});

function draw_mortgage_chart(equity, loan_balance, property_value) {
	var data = convertChartData(equity, loan_balance, property_value);
	if (data.length) {
		$('.wrap-mortgage .tooltip').remove();
		var svg = d3.select("#mortgage-chart").html(''),
			margin = {top: 20, right: 20, bottom: 30, left: 50},
			width = +svg.attr("width") - margin.left - margin.right,
			height = +svg.attr("height") - margin.top - margin.bottom,
			color = d3.scaleOrdinal().range([{x:"#d24359",y:"#d24359"},{x:"#6ab358",y:"#6AB358"},{x:"#7bc0d3",y:"#7bc0d3"},]),
			color_key = {Loan_balance: {x:"#d24359", y:"#d24359"}, Equity: {x:"#6ab358", y:"#6AB358"}, Property_value: {x:"#7bc0d3", y:"#7bc0d3"}},
			color1 = [{x:"#d24359", y:"#d24359"},{x:"#6ab358", y:"#6AB358"},{x:"#7bc0d3", y:"#7bc0d3"}],
			keys = [],
			maxNum = 0,
			minNum = 0,
			mar = 130;

		var x = d3.scaleTime()
			.range([0, width]);
		
		var y = d3.scaleLinear()
			.range([height, 0]);

		var xAxis = d3.axisBottom(x)
		    .ticks((width + 2) / (height + 2) * 7)
		    .tickSize(height)
		    .tickPadding(18 - height)
		    .tickFormat(multiFormat);
		
		var yAxis = d3.axisRight(y)
		    .ticks(7)
		    .tickSize(width)
		    .tickPadding(-(width + 50));

		for (var prop in data[0]) {
		    if (data[0].hasOwnProperty(prop) && prop != 'Year') {
		        keys.push(prop);
		    }
		}
		color.domain(d3.keys(data[0]).filter(function(key) {
		    if(key != "Year"){
		        return key ;
		    }
		}));
		var browsers = color.domain().map(function(name) {
			return {
			    name: name,
			    values: data.map(function(d) {
			    return {
			        date: moment(d.Year),
			        y: d[name],
			        y0:0
			    };
			  })
			};
		});
		for(var index in data) {
			if (maxNum < Math.max(data[index]['Equity'], data[index]['Loan_balance'], data[index]['Property_value'])) {
				maxNum = Math.max(data[index]['Equity'], data[index]['Loan_balance'], data[index]['Property_value']);
			}
			
			if (minNum > Math.min(data[index]['Equity'], data[index]['Loan_balance'], data[index]['Property_value'])) {
				minNum = Math.min(data[index]['Equity'], data[index]['Loan_balance'], data[index]['Property_value']);
			}
			data[index]['Year'] = new Date(data[index]['Year']);
			data[index]['date'] = moment(data[index]['Year'])
		}
		
		x.domain(d3.extent(data, function(d) { return d['Year']; }));
		y.domain([minNum, maxNum]);
		
		var g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		var gX = g.append("g")
			.attr("transform", "translate(0," + height + ")")
			.attr("class", "axis x")
			.call(xAxis);
		var gY = g.append("g")
			.call(yAxis)
			.attr("class", "axis y")
			.append("text")
			.attr("fill", "#000")
			.attr("transform", "rotate(-90)")
			.attr("y", 6)
			.attr("dy", "0.71em")
			.attr("text-anchor", "end");
		var gpath = g.append("g");
		var cir = g.append("g").attr("class","cricle");
		
		var area = d3.area()
			.x(function(d) {return x(d.date); })
			.y1(function(d) { return y(d.y); });
		area.y0(y(0));
		var line = d3.line()
			.x(function(d) {return x(d.date); })
			.y(function(d) { return y(d.y);});
		
		var vars = g.selectAll(".vars")
			.data(browsers)
			.enter().append("g")
			.attr("class", "vars");
		
		vars.append("path")
			.attr("class", function(d,i) {
				return (d.name);
			})
			.attr("d", function(d) {
				return area(d.values);
			})
			.style("fill",function(d,i) {
				return (  "url(#gradient"+i+")");
			} )
			.style("fill-opacity", 0.9);
		
		vars.append("path")
			.attr("class", function(d) {
				return "line "+(d.name);
			} )
			.attr("d", function(d) {
				return line(d.values);
			})
			.style("stroke", function(d,i) {
				return color1[i].x;
			})
			.style("fill-opacity", 0);
		var scrubber = g.append("g")
			.attr("class", "the-scrubber");
		var tooltip = d3.select(".wrap-mortgage").append('div')
			.attr('class', 'tooltip');
		
		g.append("g")
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
				$('.wrap-mortgage .tooltip').css({'opacity': '1', 'position': 'initial'});
				if(i < (data.length/2)){
					tooltip.append('div')
						.attr('class','mrr-graph__tooltip')
						.attr('style','position:absolute;opacity:1;top:'+(y(data[i].Loan_balance) + 70)+'px;left:'+(x(data[i].date)+250)+'px;')
						.html(function() {
							html = "<div class='current'>"+moment(data[i].date).format("YYYY-MM-DD")+"</div>";
							html += '<div class="col-table"><div class="col names">';
							html += '<span class="property-value">Property Value</span>';
							html += '<span class="equity">Equity</span>';
							html += '<span class="loan-balance">Loan balance</span>';
							html += '<span class="total">Total Value</span>'
							html += '</div>';
							html += '<div class="col amounts">';
							html += '<span class="property-value">$'+data[i].Property_value.format(2)+'</span>';
							html += '<span class="equity">$'+data[i].Equity.format(2)+'</span>';
							html += '<span class="loan-balance">$'+data[i].Loan_balance.format(2)+'</span>';
							html += '<span class="total">$'+((data[i].Property_value - data[i].Loan_balance).format(2))+'</span>';
							html += '</div>';
							return html;
						});
				}else{
					tooltip.append('div')
						.attr('class', 'mrr-graph__tooltip')
						.attr('style','position:absolute;opacity:1;top:'+(y(data[i].Loan_balance) + 70)+'px;left:'+(x(data[i].date)-120)+'px;')
						.html(function() {
							html = "<div class='current'>"+moment(data[i].date).format("YYYY-MM-DD")+"</div>";
							html += '<div class="col-table"><div class="col names">';
							html += '<span class="property-value">Property Value</span>';
							html += '<span class="equity">Equity</span>';
							html += '<span class="loan-balance">Loan balance</span>';
							html += '<span class="total">Total Value</span>'
							html += '</div>';
							html += '<div class="col amounts">';
							html += '<span class="property-value">$'+data[i].Property_value.format(2)+'</span>';
							html += '<span class="equity">$'+data[i].Equity.format(2)+'</span>';
							html += '<span class="loan-balance">$'+data[i].Loan_balance.format(2)+'</span>';
							html += '<span class="total">$'+((data[i].Property_value - data[i].Loan_balance).format(2))+'</span>';
							html += '</div>';
							return html;
					});
				}
				
				scrubber.append('rect')
					.attr('x',function () {
						return (x(data[i].date));
					})
					.attr('y',0)
					.attr('width',2)
					.attr('height',height)
					.attr('fill',"white");
					
				scrubber.append('circle')
					.data([data])
					.attr('cx',function () {
						return x(data[i].date);
					})
					.attr('cy',function () {
						return y(data[i].Loan_balance);
					})
					.attr('r',5)
					.attr('fill',function(d,i) {
						return color1[0].x;
					})
					.attr('class',"Loan_balance");
					
				scrubber.append('circle')
					.data([data])
					.attr('cx',function () {
						return x(data[i].date);
					})
					.attr('cy',function () {
						return y(data[i].Equity);
					})
					.attr('r',5)
					.attr('fill',function(d,i) {
						return color1[1].x;
					})
					.attr('class',"Equity");
				
				scrubber.append('circle')
					.data([data])
					.attr('cx',function () {
						return x(data[i].date);
					})
					.attr('cy',function () {
						return y(data[i].Property_value);
					})
					.attr('r',5)
					.attr('fill',function(d,i) {
						return color1[2].x;
					})
					.attr('class',"Property_value");
		
				$("#amort-table tbody").animate({
					scrollTop: $("#amort-table tbody tr").last().height() * ((i+1) - 4)
				}, 10);
				$("#amort-table tbody tr:eq("+ (i) +")").addClass("active");
			})
			.on("mouseout", function(e,i) { 
				scrubber
					.attr('opacyty',0)
					.html("");
				d3.select(".tooltip").html("");
				$("#amort-table tbody tr:eq("+ (i) +")").removeClass("active");
			});
		
		for(var k in keys) {
			var key = keys[k];
			var gradient = svg.append("svg:defs").append("svg:linearGradient")
				.attr("id", "gradient"+k)
				.attr("x2", "0%")
				.attr("y2", "100%");
			gradient.append("svg:stop")
				.attr("offset", "0%")
				.attr("stop-color", color_key[key].x)
				.attr("stop-opacity", 0.3);
			gradient.append("svg:stop")
				.attr("offset", "100%")
				.attr("stop-color", color_key[key].y)
				.attr("stop-opacity", 0.3);
			
			var legend =   svg.append("g").attr("transform", "translate(" + (width - mar) + "," + 10 + ")");
			legend.append("text")
				.attr("transform","translate(15,5)")
				.text(key.replace("_"," "))
				.attr("style","font-size: 13px;");
			legend.append("circle")
				.attr("r", 7)
				.attr("transform","translate(0,0)")
				.style("fill", "url(#gradient"+k+")")
				.style("stroke", "none");
			mar += 150;
		}
	}
}

function convertChartData(equity, loan_balance, property_value) {
	var result = [];
	for(var i in equity) {
		var equi = equity[i],
			loan = loan_balance[i],
			prop = property_value[i],
			year = new Date(equi[0] * 1000);
		result.push({
			Year: year.getFullYear() +'-'+ (year.getMonth() + 1) +'-'+ year.getDate(),
			Loan_balance: loan[1] ? (Math.round(loan[1] * 100) / 100) : 0,
			Equity: equi[1] ? (Math.round(equi[1] * 100) / 100) : 0,
			Property_value: prop[1] ? (Math.round(prop[1] * 100) / 100) : 0,
		});
	}
	
	return result;
}

function multiFormat(date) {
	var formatMillisecond = d3.timeFormat(".%L"),
	    formatSecond = d3.timeFormat(":%S"),
	    formatMinute = d3.timeFormat("%I:%M"),
	    formatHour = d3.timeFormat("%I %p"),
	    formatDay = d3.timeFormat("%a %d"),
	    formatWeek = d3.timeFormat("%b %d"),
	    formatMonth = d3.timeFormat("%b"),
	    formatYear = d3.timeFormat("%Y");
	return (d3.timeSecond(date) < date ? formatMillisecond
			: d3.timeMinute(date) < date ? formatSecond
			: d3.timeHour(date) < date ? formatMinute
			: d3.timeDay(date) < date ? formatHour
			: d3.timeMonth(date) < date ? (d3.timeWeek(date) < date ? formatDay : formatWeek)
			: d3.timeYear(date) < date ? formatMonth
			: formatYear)(date);
}

/*
 * updateAmortizationSchedule
 * @param table_html: string (html content of amortization table)
 */
function updateAmortizationSchedule(table_html) {
	if($('#lblamortization_schedule').length) {
		$('#lblamortization_schedule').html(table_html);
	}
}

draw_mortgage_chart([{{ p.calc.chart_equity_value }}], [{{ p.calc.chart_loan_balance }}], [{{ p.calc.chart_property_value }}]);
