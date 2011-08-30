#!/usr/bin/env python

import sublime, sublime_plugin
import os, os.path
from os.path import join
import re

class GenerateCappuccinoCompletionsCommand(sublime_plugin.WindowCommand):
    SOURCE_RE = re.compile(r"^(CP|CG|CA)\w+\.j$")
    IMPLEMENTATION_RE = re.compile(r"^@implementation\s+([\w\d]+)(?:\s*(?:(\([\w\d]+\))|:\s*([\w\d]+(?:\s*\<.+?\>)?)))?(.*?)^@end", re.MULTILINE + re.DOTALL)
    METHOD_RE = re.compile(r"^([-+])\s*\([\w\d]+\)([\w\d]+)(.*)$", re.MULTILINE)
    SIGNATURE_RE = re.compile(r"([\w\d]+?:)(\([\w\d]+(?: ?<[\w\d]+>)?\)[\w\d]+)")
    STRIPPED_SIGNATURE_RE = re.compile(r"[\w\d]+?:")
    CONSTANT_RE = re.compile(r"^([A-Z][\w\d]+)\s*=\s*.+;", re.MULTILINE)

    FUNCTION_RE = re.compile(r"^(?:function |_function\()(C[AGP][\w\d]+)\((.*?)\)", re.MULTILINE)
    FUNCTION_ARG_TEMPLATE = "${{{0}:{1}}}"
    FUNCTION_COMPLETION_TEMPLATE = "{0}({1})"

    INSTANCE_COMPLETIONS_TEMPLATE = """completions = [
{0}
]
"""

    SNIPPET_TEMPLATE = '    ("{0}", "{1}")'
    SNIPPET_PARAMETER_TEMPLATE = "{0}${{{1}:{2}}}"

    CLASS_COMPLETIONS_TEMPLATE = """superclass = "{0}"
completions = [
{1}
]
"""

    OBJECTIVEJ_SETTINGS = "Objective-J.sublime-settings"
    CAPPUCCINO_SOURCE_PATH_SETTING = "cappuccino_source"

    def __init__(self, window):
        super(GenerateCappuccinoCompletionsCommand, self).__init__(window)
        self.libPath = join(sublime.packages_path(), "Objective-J", "lib")
        self.classNames = set()
        self.inheritanceMap = {}
        self.classMethods = {}
        self.instanceMethods = {}
        self.functions = {}
        self.constants = []

    def parse_source_directory(self, path):
        for root, dirs, files in os.walk(path):
            if "Resources" in dirs:
                dirs.remove("Resources")

            for f in files:
                if self.SOURCE_RE.match(f):
                    self.parse_source(join(root, f))

    def add_method_signature(self, className, signature, isClassMethod):
        # Strip the signature of types and parameter names for comparison
        if ":" in signature:
            strippedSignature = "".join(self.STRIPPED_SIGNATURE_RE.findall(signature))
            splitSignature = self.SIGNATURE_RE.findall(signature)
        else:
            strippedSignature = signature
            splitSignature = None

        if isClassMethod:
            info = (strippedSignature, splitSignature)

            if not self.classMethods.has_key(className):
                self.classMethods[className] = [info]
            else:
                self.classMethods[className].append(info)
        else:
            self.instanceMethods[strippedSignature] = splitSignature

    def parse_implementation(self, className, body):
        matches = self.METHOD_RE.findall(body)

        for match in matches:
            signature = "".join(match[1:])

            if signature[0] == "_":
                continue

            isClassMethod = match[0] == "+"
            self.add_method_signature(className, signature, isClassMethod)

    def parse_source(self, path):
        sourceFile = open(path)
        source = sourceFile.read()
        sourceFile.close()

        implementations = self.IMPLEMENTATION_RE.findall(source)

        for className, category, superclass, body in implementations:
            if not className.startswith("_"):
                self.classNames.add(className)

                if not category and superclass:
                    self.inheritanceMap[className] = superclass

                self.parse_implementation(className, body)

        functionMatches = self.FUNCTION_RE.findall(source)

        for functionName, args in functionMatches:
            argList = []

            for index, arg in enumerate(re.split(r",\s*", args)):
                argList.append(self.FUNCTION_ARG_TEMPLATE.format(index + 1, arg))

            self.functions[functionName] = self.FUNCTION_COMPLETION_TEMPLATE.format(functionName, ", ".join(argList))

        constantMatches = self.CONSTANT_RE.findall(source)

        for constant in constantMatches:
            self.constants.append(constant)

    def make_snippet(self, parameters):
        contents = []

        for index, parameter in enumerate(parameters):
            contents.append(self.SNIPPET_PARAMETER_TEMPLATE.format(parameter[0], index + 1, parameter[1]))

        return " ".join(contents)

    def write_instance_methods(self):
        methods = sorted(self.instanceMethods.keys(), cmp=lambda x,y: cmp(x.lower(), y.lower()))
        completions = []

        for method in methods:
            parameters = self.instanceMethods[method]

            if parameters is None:
                completions.append(self.SNIPPET_TEMPLATE.format(method, method))
            else:
                completions.append(self.SNIPPET_TEMPLATE.format(method, self.make_snippet(parameters)))

        outfile = open(join(self.libPath, "instance_methods.completions"), "w")
        outfile.write(self.INSTANCE_COMPLETIONS_TEMPLATE.format(",\n".join(completions)))
        outfile.close()

    def write_classes(self):
        completions = []

        for className in sorted(list(self.classNames)):
            completions.append(self.SNIPPET_TEMPLATE.format(className, className))

        outfile = open(join(self.libPath, "classes.completions"), "w")
        outfile.write(self.INSTANCE_COMPLETIONS_TEMPLATE.format(",\n".join(completions)))
        outfile.close()

    def write_constants(self):
        completions = []

        for constant in sorted(self.constants):
            completions.append(self.SNIPPET_TEMPLATE.format(constant, constant))

        outfile = open(join(self.libPath, "constants.completions"), "w")
        outfile.write(self.INSTANCE_COMPLETIONS_TEMPLATE.format(",\n".join(completions)))
        outfile.close()

    def write_functions(self):
        completions = []

        for functionName in sorted(self.functions.keys()):
            completions.append(self.SNIPPET_TEMPLATE.format(functionName + "()", self.functions[functionName]))

        outfile = open(join(self.libPath, "functions.completions"), "w")
        outfile.write(self.INSTANCE_COMPLETIONS_TEMPLATE.format(",\n".join(completions)))
        outfile.close()

    def write_class_methods(self):
        basePath = join(self.libPath, "class_methods")

        for className in self.classNames:
            completions = []
            methods = sorted(self.classMethods.get(className, []), cmp=lambda x,y: cmp(x[0].lower(), y[0].lower()))

            # methods is a list of (stripped signature, [parameters]) tuples
            for method in methods:
                completions.append(self.SNIPPET_TEMPLATE.format(method[0], self.make_snippet(method[1]) if method[1] else method[0]))

            path = join(basePath, className + ".completions")
            outfile = open(path, "w")
            outfile.write(self.CLASS_COMPLETIONS_TEMPLATE.format(self.inheritanceMap.get(className, ""), ",\n".join(completions)))
            outfile.close()

    def run(self):
        sourcePath = sublime.load_settings(self.OBJECTIVEJ_SETTINGS).get(self.CAPPUCCINO_SOURCE_PATH_SETTING)

        if not sourcePath:
            self.window.show_input_panel("Path to Cappuccino source:", "", self.generate, None, None)
        else:
            self.generate(sourcePath)

    def generate(self, sourcePath):
        if not sourcePath:
            return

        if not os.path.isdir(sourcePath):
            sublime.error_message("'{0}' is not a valid path to a directory.".format(sourcePath))
            return

        appKitPath = join(sourcePath, "AppKit")
        foundationPath = join(sourcePath, "Foundation")

        if not os.path.isdir(appKitPath) or not os.path.isdir(foundationPath):
            sublime.error_message("'{0}' does not appear to be a Cappuccino source directory.".format(sourcePath))
            return

        self.parse_source_directory(appKitPath)
        self.parse_source_directory(foundationPath)
        self.write_instance_methods()
        self.write_class_methods()
        self.write_classes()
        self.write_functions()
        self.write_constants()

        # If we make it this far, save the path so next time the user does not have to enter it
        settings = sublime.load_settings(self.OBJECTIVEJ_SETTINGS)
        settings.set(self.CAPPUCCINO_SOURCE_PATH_SETTING, sourcePath)
        sublime.save_settings(self.OBJECTIVEJ_SETTINGS)

        sublime.error_message("Cappuccino completions successfully generated.")

    def is_enabled(self):
        activeView = self.window.active_view()

        if activeView:
            return activeView.settings().get("syntax").endswith("/Objective-J.tmLanguage")
        else:
            return False
