NOTE: x.x.x indicates the current version number.

- Download latest jquery UI concatenated JS & CSS zip (jquery-ui-x.x.x.zip) from
  https://jqueryui.com/download/all/ and copy following contents into the
  static/js/vendor/jquery/ui/x.x.x directory:

        all .js files
        all .css files

 - Download latest jquery UI Themes zip (jquery-ui-themes-x.x.x.zip) from
   "https://jqueryui.com/download/all/" , choose the theme from the
    the zip's subdirectories, then:

        - copy the contents of the images directory into
          static/js/vendor/jquery/ui/x.x.x/images
        - copy jquery-ui.css, jquery.ui.min.css and theme.css into
          static/js/vendor/jquery/ui/x.x.x. (This may overwrite some existing files from
          previous step).

- Also upgrade to the latest jquery at the same time; Download the zip and copy the
    jquery-x.x.x.min.js into the static/js/vendor/jquery/x.x.x directory


