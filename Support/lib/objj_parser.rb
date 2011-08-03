#!/usr/bin/env ruby
#
# objj_parser.rb
#
# A slight modification of the original by joachimm (https://github.com/joachimm).
# No copyright or license is asserted in the original file, but it is publicly
# available on github.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

class Lexer
    include Enumerable

    def initialize
        @label   = nil
        @pattern = nil
        @handler = nil
        @input   = nil

        reset

        yield self if block_given?
    end

    def input(&reader)
        if @input.is_a? self.class
            @input.input(&reader)
        else
            class << reader
                alias_method :next, :call
            end

            @input = reader
        end
    end

    def add_token(label, pattern, &handler)
        unless @label.nil?
            @input = clone
        end

        @label   = label
        @pattern = /(#{pattern})/
        @handler = handler || lambda { |label, match| [label, match] }

        reset
    end

    def next(peek = false)
        while @tokens.empty? and not @finished
            new_input = @input.next

            if new_input.nil? or new_input.is_a? String
                @buffer    += new_input unless new_input.nil?
                new_tokens =  @buffer.split(@pattern)

                while new_tokens.size > 2 or (new_input.nil? and not new_tokens.empty?)
                    @tokens << new_tokens.shift
                    @tokens << @handler[@label, new_tokens.shift] unless new_tokens.empty?
                end

                @buffer   = new_tokens.join
                @finished = true if new_input.nil?
            else
                separator, new_token = @buffer.split(@pattern)
                new_token            = @handler[@label, new_token] unless new_token.nil?
                @tokens.push( *[ separator,
                    new_token,
                    new_input ].select { |t| not t.nil? and t != "" } )
                reset(:buffer)
            end
        end

        peek ? @tokens.first : @tokens.shift
    end

    def peek
        self.next(true)
    end

    def each
        while token = self.next
            yield token
        end
    end

    private

    def reset(*attrs)
        @buffer   = String.new if attrs.empty? or attrs.include? :buffer
        @tokens   = Array.new  if attrs.empty? or attrs.include? :tokens
        @finished = false      if attrs.empty? or attrs.include? :finished
    end
end


class ObjcParser

    attr_reader :list

    def initialize(args)
        @list = args
    end

    def get_position
        return nil,nil if @list.empty?
        has_message = true

        a = @list.pop
        endings = [:close,:post_op,:at_string,:at_selector,:identifier]
        openings = [:open,:return,:control]

        if a.tt == :identifier && !@list.empty? && endings.include?(@list[-1].tt)
            insert_point = find_object_start
        else
            @list << a
            has_message = false unless methodList
            insert_point = find_object_start
        end

        return insert_point, has_message
    end

    def methodList
        old = Array.new(@list)
        a = selector_loop(@list)

        if !a.nil? && a.tt == :selector
            internal = Array.new(@list)
            b = a.text

            until internal.empty?
                tmp = selector_loop(internal)
                return true if tmp.nil?

                b = tmp.text + b
            end
        end

        @list = old
        return false
    end

    def selector_loop(l)
        until l.empty?
            obj = l.pop

            case obj.tt
                when :selector
                    return obj
                when :close
                    return nil if match_bracket(obj.text,l).nil?
                when :open
                    return nil
            end
        end

        return nil
    end

    def match_bracket(type,l)
        partner = {"]"=>"[",")"=>"(","}"=>"{"}[type]
        up = 1

        until l.empty?
            obj = l.pop

            case obj.text
                when type
                    up += 1
                when partner
                    up -= 1
            end

            return obj.beg if up == 0
        end
    end

    def find_object_start
        openings = [:operator,:selector,:open,:return,:control]

        until @list.empty? || openings.include?(@list[-1].tt)
            obj = @list.pop

            case obj.tt
                when :close
                    tmp = match_bracket(obj.text, @list)
                    b = tmp unless tmp.nil?
                when :star
                    b, ate = eat_star(b,obj.beg)
                    return b unless ate
                when :nil
                    b = nil
            else
                b = obj.beg
            end
        end

        return b
    end

    def eat_star(prev, curr)
        openings = [:operator,:selector,:open,:return,:control,:star]

        if @list.empty? || openings.include?(@list[-1].tt)
            return curr, true
        else
            return prev, false
        end
    end
end

def escape_snippet(str)
    str.to_s.gsub(/(?=[$`\\])/, '\\')
end

if __FILE__ == $PROGRAM_NAME
    require "stringio"
    line = ENV['TM_CURRENT_LINE']
    caret_placement =ENV['TM_LINE_INDEX'].to_i - 1

    up = 0
    pat = /"(?:\\.|[^"\\])*"|\[|\]/

    line.scan(pat).each do |item|
        case item
        when "["
            up += 1
        when "]"
            up -=1
        end
    end

    if caret_placement ==-1
        print "]$0" + escape_snippet(line[caret_placement + 1..-1])
        exit
    end

    if  up != 0
        print escape_snippet(line[0..caret_placement]) + "]$0" + escape_snippet(line[caret_placement + 1..-1])
        exit
    end

    to_parse = StringIO.new(line[0..caret_placement])

    lexer = Lexer.new do |l|
        l.add_token(:return,  /\breturn\b/)
        l.add_token(:nil, /\bnil\b/)
        l.add_token(:control, /\b(?:if|while|for|do)(?:\s*)\(/)# /\bif|while|for|do(?:\s*)\(/)
        l.add_token(:at_string, /"(?:\\.|[^"\\])*"/)
        l.add_token(:selector, /\b[A-Za-z_0-9]+:/)
        l.add_token(:identifier, /\b[A-Za-z_0-9]+\b/)
        l.add_token(:bind, /(?:->)|\./)
        l.add_token(:post_op, /\+\+|\-\-/)
        l.add_token(:at, /@/)
        l.add_token(:star, /\*/)
        l.add_token(:close, /\)|\]|\}/)
        l.add_token(:open, /\(|\[|\{/)
        l.add_token(:operator,   /[&-+\/=%!:\,\?;<>\|\~\^]/)

        l.add_token(:terminator, /;\n*|\n+/)
        l.add_token(:whitespace, /\s+/)
        l.add_token(:unknown,    /./)

        l.input { to_parse.gets }
        #l.input {STDIN.read}
    end

    offset = 0
    tokenList = []
    A = Struct.new(:tt, :text, :beg)

    lexer.each do |token|
        tokenList << A.new(*(token<<offset)) unless [:whitespace,:terminator].include? token[0]
        offset += token[1].length
    end

    if tokenList.empty?
        print escape_snippet(line[0..caret_placement]) + "]$0" + escape_snippet(line[caret_placement + 1..-1])
        exit
    end

    par = ObjcParser.new(tokenList)
    b, has_message = par.get_position

    if !line[caret_placement + 1].nil? && line[caret_placement + 1].chr == "]"
        if b.nil? || par.list.empty? || par.list[-1].text == "["
            print escape_snippet(line[0..caret_placement]) + "]$0" + escape_snippet(line[caret_placement + 2..-1])
            exit
        end
    end

    if b.nil?
        print escape_snippet(line[0..caret_placement]) + "]$0" + escape_snippet(line[caret_placement + 1..-1])
    elsif !has_message && (b < caret_placement )
        print escape_snippet(line[0..b-1]) unless b == 0
        ins = (/\s/ =~ line[caret_placement].chr ? "$0]" : " $0]")
        print "[" + escape_snippet(line[b..caret_placement]) + ins + escape_snippet(line[caret_placement + 1..-1])
    elsif b < caret_placement
        print escape_snippet(line[0..b-1]) unless b == 0
        print "[" + escape_snippet(line[b..caret_placement]) + "]$0" + escape_snippet(line[caret_placement + 1..-1])
    else
        print escape_snippet(line[0..caret_placement]) + "]$0" + escape_snippet(line[caret_placement + 1..-1])
    end
end
