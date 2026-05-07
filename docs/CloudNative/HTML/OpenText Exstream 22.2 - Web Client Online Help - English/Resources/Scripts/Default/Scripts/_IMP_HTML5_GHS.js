
	
	var navClosedByUser = false;
	var navClosedByScript = false;
	var navForcedOpenByUser = false;
	
	$(document).ready(function () {
	
		// Add styles to page
		// Fix issue with cut off selection highlights in TocEntry
		// Normal font weight for bottom nodes
		
		$("<style/>")
		.prop("type", "text/css")
		.html("\
			ul.tree {\
				overflow: hidden;\
			}\
			li.tree-node-leaf div {\
				font-weight: normal;\
			}\
		")
		.appendTo("head");
		
		
		// Reposition logo and add wordmark (which is "Help", and not the actual product name)
	
		$('#header>a').css('color','black');
		$('#header>a>h1')
		.css({
			'position': 'relative',
			'left': '50%',
			'margin-left': '-130px',
			'float': 'left'
		});
		$('<div/>')
			.attr('id','wordmarkDivider')
			.css({
				'position': 'relative',
				'border-left': 'thick solid black',
				'border-left-width': '1px',
				'left': '50%',
				'margin-left': '8px',
				'margin-top': '18px',
				'height': '24px',
				'float': 'left'
			})
			.insertAfter( $('#header>a>h1') );
		$('<div/>')
			.attr('id','wordmark')
			.css({
				'position': 'relative',
				'margin-left': '8px',
				'margin-top': '18px',
				'left': '50%',
				'height': '25px',
				'float': 'left',
				'font-size': '20px'
			})
			.html('Help') // NEEDS TO BE VARIABLE FOR LOCALIZATION
			.insertAfter( $('#wordmarkDivider') );
		
		
		// Create search panel in nav pane
		
		$('<div/>')
			.attr('id','searchPanel')
			.css({
				'background-color': '#ececec',
				'height': '63px',
				'width': '100%',
				'border-top': '1px #cccbcb solid',
				'border-bottom': '1px #cccbcb solid'
			})
			.prependTo('#navigation');
			
		
		// Create space for doc tabs in content pane
		
		$('<div/>')
			.attr('id','docMenu')
			.css({
				'background-color': '#ececec',
				'height': '63px',
				'border-top': '1px #cccbcb solid',
				'border-bottom': '1px #cccbcb solid',
				'margin-left': '-5px'
			})
			.prependTo('#contentBody');
			
		
		// Add doc tab
		
		$('<div/>')
			.attr('id','activeDocTab')
			.css({
				'background-color': '#ffffff',
				'position': 'absolute',	
				'height': '63px',
				'width': 'auto',
				'padding': '0 20px',
				'overflow': 'hidden',
				'white-space': 'nowrap',
				'border-bottom': '1px #cccbcb solid',
			})
			.appendTo('#docMenu');
			
		
		// Loading from bannerTitle.html doesn't work locally, use header-title meta tag from target instead (https://forums.madcapsoftware.com/viewtopic.php?f=9&t=18878)
		
		var headerTitle = $("meta[name='header-title']").attr("content");
		
		
		// Add doc title to tab
		
		$('<p/>')
			.attr('id','activeDocTab')
			.text(headerTitle)
			.css({
				'font-size': '13px',
				'font-weight': 'bold',
				'margin': '0',
				'height': '34px',
				'padding-top': '25px',
				'border-bottom': '4px #0072aa solid'
			})
			.appendTo('#activeDocTab');
		
		
		// Move search box to nav pane
		
		$('.search-bar')
			.prependTo( $('#searchPanel') )
			.css({
				'top': '7px',
				'margin': '7px',
				'left': '0px',
				'width': 'calc(100% - 14px)'
			});
		$('#search-field')
			.css({
				'width': 'calc(100% - 42px)',
				'padding-left': '8px'
			});
		
		
		// Make space for search box above nav pane (tabs-panel), other box and appearance adjustments
		
		$('.tabs-panel').css('top', '65px');
		$('#body').css('top', '71px');
		$('#contentBodyInner')
			.css({
				'top': '72px',
				'bottom': '42px',
				'border': 'none'
			});
		$('#toc').css({
			'top': '0',
			'right': '0',
			'left': '0',
		});
		
		
		// Fix issue with "Contents" tab name appearing in white
		
		$('.tabs-nav').css('display', 'none');
		
		
		// Move navigation buttons to footer
		// Can't adjust to bottom of iframe contents due to same-origin policy and local usage
		
		$('<div/>')
			.attr('id', 'navfooter')
			.css({
				'background-color': '#EEE',
				'position': 'absolute',
				'left': '0',
				'right': '0',
				'bottom': '0',
				'height': '40px',
				'margin-left': '0',
				'margin-right': '8px',
				'overflow': 'hidden'
			})
			.appendTo('#contentBody')
			.append( $('.toolbar-buttons') );
			
		
		// Adjust toolbar buttons and keep from wrapping
		// Because of floats used for left/right buttons, the right buttons still wrap below the
		// left as a whole, but this only happens in extreme/unlikely circumstances
		
		$('.button-group-container-left')
			.css({
				'overflow': 'hidden',
				'white-space': 'nowrap'
			});
		$('.button-group-container-right')
			.css({
				'overflow': 'hidden',
				'white-space': 'nowrap'
			});
		$('.button')
			.css({
				'display': 'inline-block',
				'float': 'none',
				'margin': '0px 1px'
			});
		
		// Determine whether navigation pane is closed and set global variable
		navClass = $('#navigation').attr('class');
		if ( navClass == 'nav-closed' ){
					navClosedByUser = true;
				} else {
					navClosedByUser = false;
				}
		
		// Determine whether nav pane should be open based on current window size
		setTimeout(checkNavPaneAfterResize, 200);
		
		//Set navigation hotkeys
		$(document).keyup(function(e) {
		  switch (e.key) {
			case 'ArrowLeft':
				prevTopic();
				break;
			case 'ArrowRight':
				nextTopic();
		  }
		});
			
	});
	
	var rtime;
	var timeout = false;
	var delta = 200;
	
	// Set timeout to determine end of resize action
	$(window).resize(function() {
		rtime = new Date();
		if (timeout === false) {
			var win = $(window);
			var navClass = $('#navigation').attr('class');
			if ( win.width() >= 768 ) {
				if ( navClass == 'nav-closed' && navClosedByScript == false){
						navClosedByUser = true;
						navForcedOpenByUser = false;
					} else {
						navClosedByUser = false;
						navForcedOpenByUser = false;
					}
				} else {
					if ( navClass != 'nav-closed' && navClosedByScript == true){
						navForcedOpenByUser = true;
					} else {
						navForcedOpenByUser = false;
					}
				}
			timeout = true;
			setTimeout(resizeEnd, delta);
		}
	});
	
	// Determine whether nav pane should close at end of resize action
	function resizeEnd() {
		if (new Date() - rtime < delta) {
			setTimeout(resizeEnd, delta);
		} else {
			timeout = false;
			checkNavPaneAfterResize();
		}               
	}
	
	function checkNavPaneAfterResize() {
		var win = $(window);
		var navClass = $('#navigation').attr('class');
		if (win.width() < 768) {
			if ( navClass != 'nav-closed' && navForcedOpenByUser == false ){
				$('#show-hide-navigation').click();
				navClosedByScript = true;
			}
		} else {
			navClosedByScript = false;
			if ( navClass == 'nav-closed' && navClosedByUser == false){
				$('#show-hide-navigation').click();
			}
		}
	}

	//Topic navigation
	function nextTopic() {
		$(".next-topic-button").click()
	}
	
	function prevTopic() {
		$(".previous-topic-button").click()
	}
	
		
