import sublime, sublime_plugin
import os.path

class CappuccinoCompletions(sublime_plugin.EventListener):
    LIB_PATH = os.path.join(sublime.packages_path(), "Objective-J", "lib")
    CLASS_METHODS_PATH = os.path.join(LIB_PATH, "class_methods")
    DIVIDER = "-------- {0} -------"
    SYMBOL_SUFFIXES = {
        "classes": " [c]",
        "constants": " [k]",
        "functions": "()",
        "instance_methods": " [m]"
    }

    def _on_query_completions(self, view, prefix, locations):
        if not view.settings().get("syntax").endswith("/Objective-J.tmLanguage") or len(locations) > 1:
            return []

        location = locations[0]
        completions = []

        # See if we are in a bracketed scope
        scopes = view.scope_name(location).split()

        if "meta.bracketed.js.objj" in scopes:
            # Go back until we find the closest open bracket
            while True:
                location -= 1
                
                if view.substr(location) == "[":
                    break

            # Go forward to the first character after the [
            # and get the next word
            location += 1
            region = view.word(location)
            symbol = view.substr(region)
            
            # We are looking for a class name, which must be at least
            # 3 characters (2 character prefix + name) and must be a valid Cappuccino class.
            if len(symbol) > 2 and self.is_class_name(symbol):
                prefix = prefix.lower()

                while True:
                    superclass, classCompletions = self.read_class_methods(symbol, prefix)

                    # Filter out duplicates
                    for index in range(len(classCompletions) - 1, -1, -1):
                        signature = classCompletions[index][0]

                        if filter(lambda x: x[0] == signature, completions):
                            del classCompletions[index]

                    if len(classCompletions):
                        completions += classCompletions

                    if superclass:
                        symbol = superclass
                    else:
                        break

                return completions

            # If we get here, we are in a bracketed scope, which means instance methods are valid
            self.append_completions("instance_methods", completions)

        # If we get here, add everything but class/instance methods
        self.append_completions("classes", completions, prefix)
        self.append_completions("functions", completions, prefix)
        self.append_completions("constants", completions, prefix)
        return completions

    def is_class_name(self, name):
        path = os.path.join(self.CLASS_METHODS_PATH, name + ".completions")
        return (os.path.exists(path), path)
        
    def read_class_methods(self, className, prefix):
        print "read_class_methods({0})".format(className)
        isClassName, path = self.is_class_name(className)

        if isClassName:
            try:
                localVars = {}
                execfile(path, globals(), localVars)
                return (localVars["superclass"], localVars["completions"] or [])
            except Exception as ex:
                print ex
                pass
        
        return ("", [])

    def append_completions(self, symbolType, completions, prefix):
        print "append_completions({0})".format(symbolType)
        path = os.path.join(self.LIB_PATH, symbolType + ".completions")

        if os.path.exists(path):
            try:
                localVars = {}
                execfile(path, globals(), localVars)
                symbolCompletions = localVars["completions"]

                if len(symbolCompletions):
                    if prefix:
                        symbolCompletions = [completion[0] + self.SYMBOL_SUFFIXES[symbolType] for completion in symbolCompletions]
                    else:
                        completions.append((self.DIVIDER.format(symbolType), " "))

                completions += symbolCompletions
            except Exception as ex:
                print ex
                pass
