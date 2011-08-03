# Sublime Text 2 bundle for Cappuccino development
Based on the TextMate Cappuccino bundle: https://github.com/malkomalko/Cappuccino.tmbundle

To install with Git, first make sure to remove any old Cappuccino or Objective-J bundles then:

    - git clone git://github.com/aparajita/Cappuccino-Sublime.git
    - Copy the Cappuccino-Sublime directory to the Sublime Text packages directory:
        OS X: ~/Library/Application Support/Sublime Text 2
        Linux: ~/.Sublime Text 2
        Windows: %APPDATA%\Sublime Text 2

## Features

* Language/Syntax aware theme coloring
* Smart formatting of class/method symbol list
* Automatic context-aware bracket balancing
* Lookup documentation for class, method, or other symbol in Ingredients (OS X only)
* Snippets for:
  * Core
    * Snippets for generating classes/categories/importing/accessors/delegates/selectors
  * AppKit
    * (text) Label
    * (text) TextField
    * (text) Rounded TextField
  * Debugging
    * Log rect to console
    * Log point to console
    * Log size to console
    * Log inset to console
    * Log message to console
  * Resizing Masks
    * Resize Full Width/Height
    * Fixed Center
    * Fixed Top Left
    * Fixed Top Right
    * Fixed Bottom Right
    * Fixed Bottom Left
    * Resize Height Fixed Left
    * Resize Height Fixed Right
    * Resize Width Fixed Top
    * Resize Width Fixed Bottom
  * Utilities
    * (rect) CGRectGetWidth
    * (rect) CGRectGetHeight
    * (rect) CGRectMakeZero
    * (rect) CGRectMake
    * (color) common CPColor methods
