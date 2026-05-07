// This init file is necessary because Flare automatically modifies relative paths in <script> tags,
// but not in actual JS. First step is to set the relative path from this script, and then we use
// that as the baseUrl for require.config before using requireJS to load scripts

var jsFileLocation = $('script[src*=_IMP_init]').attr('src');  // the js file path
jsFileLocation = jsFileLocation.replace('_IMP_init.js', '');   // the js folder path

require.config({
	baseUrl: jsFileLocation
});

requirejs(['_IMP_imageMapResizer.min'], function () {
	$('map').imageMapResize();
});