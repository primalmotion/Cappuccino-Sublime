import sublime
import sublime_plugin
import re
import subprocess


class LookupSymbolCommand(sublime_plugin.TextCommand):
    INGREDIENTS_SEARCH_COMMAND = '''
tell application "Ingredients"
    search front window query "{0}"
    activate
end tell
'''

    def __init__(self, view):
        super(LookupSymbolCommand, self).__init__(view)
        self.searchHandlers = {
            "ingredients": self.lookupInIngredients
        }

    def is_enabled(self):
        return sublime.platform() == "osx" and self.view.settings().get("syntax").endswith("/Objective-J.tmLanguage")

    def run(self, edit, target=None):
        if not target:
            target = self.view.settings().get("cappuccino_lookup_target")

            if not target:
                sublime.error_message("No target application has been set for symbol lookups.")
                return

        msg = self.lookup(target)

        if msg:
            sublime.error_message(msg)

    def lookup(self, target):
        region = self.view.sel()[0]
        region = sublime.Region(region.a, region.b)
        wordRegion = self.view.word(region)
        word = self.view.substr(wordRegion)

        # If the region is empty (a cursor) and is to the right of a non-empty word,
        # move it one character to the left so that the scope is the scope of the word.
        if region.empty() and word and region.begin() == wordRegion.end():
            region = sublime.Region(region.a - 1, region.a - 1)

        line = self.view.substr(self.view.line(region))
        scopes = self.view.scope_name(region.begin()).split()
        searchText = ""

        if "meta.implementation.declaration.js.objj" in scopes:
            matches = re.match(r'@implementation\s+(\w+)(?:\s:\s+(\w+))?', line)

            if matches:
                className = matches.group(1)
                superclassName = matches.group(2)

                if className.startswith("CP"):
                    searchText = className
                elif superclassName.startswith("CP"):
                    searchText = superclassName
                else:
                    return "Neither class is a Cappuccino class, no documentation is available."
            else:
                return "This is not a well-formed class declaration."

        elif ("meta.function-call.js.objj" in scopes) or ("meta.method-call.js.objj" in scopes):
            searchText = self.view.substr(self.view.word(region))

        elif "meta.method.js.objj" in scopes:
            matches = re.findall(r'(?:^[-+]\s*\(\w+\)(\w+:?))|(\w+:)', line)

            if len(matches):
                if len(matches) == 1:
                    searchText = ''.join(matches[0])
                else:
                    searchText = reduce(lambda x, y: ''.join(x) + ''.join(y), matches)

        elif scopes[0] == "support.class.cappuccino":
            searchText = self.view.substr(self.view.word(region))

        if not searchText:
            return "You are not within a method definition or invocation."
        else:
            searchText = re.sub(r"\bCP(?=\w+)", "NS", searchText)
            searchText = searchText.replace("Cib", "Nib")
            self.searchHandlers[target](searchText)
            return None

    def lookupInIngredients(self, searchText):
        process = subprocess.Popen(["/usr/bin/osascript"], stdin=subprocess.PIPE)

        if process:
            process.communicate(input=self.INGREDIENTS_SEARCH_COMMAND.format(searchText))
            process.stdin.close()
