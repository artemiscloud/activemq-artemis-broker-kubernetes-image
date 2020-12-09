# AMQ uses jboss-logging for logs. It supports configuration
# in a .properties file which is currently used in AMQ.
# Users that uses artemiscloud operator to deploy their
# amq brokers needs a way to change the existing logging settings
# based on their specific needs. With python doing the job
# seems better than shell script to manipulate config files
# and more maintainable.
#
# The AMQ default logging.properties file basically has the following
# parts in order.
#
# 1. License header -- Apache 2.0 license
# 2. 'loggers': a one-line text has all loggers need to configure, separated by commas
# 3. logger settings. Properties like level etc for each logger to be configured.
#    properties for each logger are grouped together (in consecutive lines not mingled
#    with other logger properties)
# 4. handler settings. Properties for each log handlers (like logger settings they
#    are grouped together for each handler and not mingled)
# 5. formatter settings. Properties for each log formatters (like patterns). Grouped
#    together like above.
# 6. other contents. Some lines are appended with comments. Empty lines are inserted
#    in between logical groups (as above of logger, handler, and formatter)
#
# In merging new user configs with existing ones, we need to preserve the existing
# format. Don't change orders of the existing parts. New elements will be appended
# to corresponding parts. This way the new config content after merging will be more
# readable to users.
#
import copy
from collections import OrderedDict
import argparse

class LoggingHeader:

    def __init__(self):
        self.header = []

    def add_header(self, line):
        self.header.append(line)

    def to_lines(self):
        return self.header


class LoggerNames:

    def __init__(self):
        self.loggers = OrderedDict()

    # logger_string passed in is a comma separated string
    def add_loggers(self, logger_string):
        logger_array = logger_string.split('=')
        logger_values = logger_array[1]
        new_loggers = logger_values.split(",")
        for l in new_loggers:
            self.loggers[l] = l

    def to_lines(self):
        return ["loggers=" + ",".join(self.loggers.values())]

    def merge(self, new_names):
        for nl in new_names.loggers:
            self.loggers[nl] = nl


class ConfigGroup:

    # group_key can be ""
    def __init__(self, group_key):
        self.group_key = group_key
        self.entries = OrderedDict()

    def add(self, entry):
        ent = copy.deepcopy(entry)
        self.entries[ent.prop_key] = ent

    def to_lines(self):
        strs = []
        for ent in self.entries.values():
            lines = ent.to_lines()
            for ln in lines:
                strs.append(ln)
        return strs

    def merge(self, new_group):
        assert self.group_key == new_group.group_key
        # self.entries.update(new_group.entries)
        for ent in new_group.entries.values():
            if ent.prop_key in self.entries:
                self.entries[ent.prop_key].merge(ent)
            else:
                self.entries[ent.prop_key] = ent


# contains config groups for loggers
# each group is keyed by logger_name
class LoggerConfig(ConfigGroup):
    # format: logger.[logger_name].prop=value
    def __init__(self, logger_name):
        ConfigGroup.__init__(self, logger_name)

    # logger_config_line: PropertyEntry
    def add_logger_prop(self, logger_prop_entry):
        # first extract loger name
        ConfigGroup.add(self, logger_prop_entry)


# contains config groups for handlers
# each group is keyed by handler_name
class HandlerConfig(ConfigGroup):
    # format handler.[handler_name].prop=value
    # or handler.[handler_name]=value
    def __init__(self, group_key):
        ConfigGroup.__init__(self, group_key)

    def add_handler_prop(self, handler_prop_entry):
        ConfigGroup.add(self, handler_prop_entry)


# the *Config classes are actually duplicated
# we can just refactor to use the Parent class. i.e. ConfigGroup
class FormatterConfig(HandlerConfig):

    def __init__(self, formatter_name):
        HandlerConfig.__init__(self, formatter_name)

    def add_formatter_prop(self, formatter_prop_entry):
        HandlerConfig.add(self, formatter_prop_entry)


# It has a key value pair and a comment
class PropertyEntry:

    def __init__(self, is_merge_comma_separated_value):
        self.comment = []
        self.prop_key = ""
        self.prop_val = ""
        self.merge_comma_separated_value = is_merge_comma_separated_value

    def add_comment(self, comment):
        self.comment.append(comment)

    def set_keyvalue(self, keyvals):
        self.prop_key = keyvals[0]
        self.prop_val = keyvals[1]

    def reset(self):
        self.prop_key = ""
        self.prop_val = ""
        self.comment = []
        self.merge_comma_separated_value = False

    def to_lines(self):
        result = []
        if len(self.comment) > 0:
            for cm in self.comment:
                result.append(cm)
        result.append(self.prop_key + "=" + self.prop_val)
        return result

    def merge(self, new_ent):
        assert self.prop_key == new_ent.prop_key
        if len(new_ent.comment) > 0:
            self.comment = new_ent.comment
        if self.merge_comma_separated_value:
            # merge
            merge_map = OrderedDict()
            existing = self.prop_val.split(',')
            for val in existing:
                merge_map[val] = val
            extra = new_ent.prop_val.split(',')
            for val in extra:
                if not val in merge_map:
                    self.prop_val = self.prop_val + "," + val
        else:
            self.prop_val = new_ent.prop_val


class LoggingProperties:
    def __init__(self):
        self.header = LoggingHeader()
        self.loggerNames = LoggerNames()
        self.loggerConfigs = OrderedDict()
        self.handlerConfigs = OrderedDict()
        self.formatterConfigs = OrderedDict()

    def add_loggers(self, loggers_string):
        self.loggerNames.add_loggers(loggers_string)

    def add_header_line(self, comment):
        self.header.add_header(comment)

    def add_logger_config(self, logger_name, entry):
        # print "Now adding a logger prop for logger [" + logger_name + "]"
        if not (logger_name in self.loggerConfigs):
            self.loggerConfigs[logger_name] = LoggerConfig(logger_name)
        self.loggerConfigs[logger_name].add_logger_prop(entry)

    def add_handler_config(self, handler_name, entry):
        # print "Now adding a handler prop for handler: [" + handler_name + "]"
        elements = entry.prop_key.split(".")
        if len(elements) == 3 and elements[0] == 'handler' and elements[1] == handler_name and elements[2] == "properties":
            entry.merge_comma_separated_value = True
        if not (handler_name in self.handlerConfigs):
            self.handlerConfigs[handler_name] = HandlerConfig(handler_name)
        self.handlerConfigs[handler_name].add_handler_prop(entry)

    def add_formatter_config(self, formatter_name, entry):
        elements = entry.prop_key.split(".")
        if len(elements) == 3 and elements[0] == 'formatter' and elements[1] == formatter_name and elements[2] == "properties":
            entry.merge_comma_separated_value = True
        if not (formatter_name in self.formatterConfigs):
            self.formatterConfigs[formatter_name] = FormatterConfig(formatter_name)
        self.formatterConfigs[formatter_name].add_formatter_prop(entry)

    #    def write_header(self, file_handle):
    #        for line in self.header.to_strings():
    #            file_handle.writelines(line)

    # don't merge/replace header
    def merge(self, new_cfg, to_replace=False):
        pass
        if to_replace:
            self.loggerNames = new_cfg.loggerNames
            self.loggerConfigs = new_cfg.loggerConfigs
            self.handlerConfigs = new_cfg.handlerConfigs
            self.formatterConfigs = new_cfg.formatterConfigs
        else:
            self.loggerNames.merge(new_cfg.loggerNames)
            for logger_cfg in new_cfg.loggerConfigs.values():
                if logger_cfg.group_key in self.loggerConfigs:
                    self.loggerConfigs[logger_cfg.group_key].merge(logger_cfg)
                else:
                    self.loggerConfigs[logger_cfg.group_key] = logger_cfg
            for handler_cfg in new_cfg.handlerConfigs.values():
                if handler_cfg.group_key in self.handlerConfigs:
                    self.handlerConfigs[handler_cfg.group_key].merge(handler_cfg)
                else:
                    self.handlerConfigs[handler_cfg.group_key] = handler_cfg
            for formatter_cfg in new_cfg.formatterConfigs.values():
                if formatter_cfg.group_key in self.formatterConfigs:
                    self.formatterConfigs[formatter_cfg.group_key].merge(formatter_cfg)
                else:
                    self.formatterConfigs[formatter_cfg.group_key] = formatter_cfg

    def write_to_file(self, file_path):
        f = open(file_path, "w")
        try:
            for hd in self.header.to_lines():
                f.write(hd + "\n")
            f.write("\n")
            for ln in self.loggerNames.to_lines():
                f.write(ln + "\n")
            f.write("\n")
            for l in self.loggerConfigs.values():
                lines = l.to_lines()
                for ll in lines:
                    f.write(str(ll) + "\n")
                f.write("\n")
            for h in self.handlerConfigs.values():
                for hh in h.to_lines():
                    f.write(str(hh) + "\n")
                f.write("\n")
            for fm in self.formatterConfigs.values():
                for ffm in fm.to_lines():
                    f.write(str(ffm) + "\n")
                f.write("\n")
        finally:
            f.close()


INIT = "init"
HEADER = "header"
HOLDING = "holding"
EXPECTING_LOGGERS = "expecting loggers"


class ParsingState:
    __state = INIT
    __cache = PropertyEntry(False)

    def __init__(self, context):
        self.__context = context

    def comment_in(self, comment):
        # print "A comment line is passing in [" + comment + "]"
        if self.__state == INIT:
            self.__context.add_header_line(comment)
            self.__state = HEADER
        elif self.__state == HEADER:
            self.__context.add_header_line(comment)
        elif self.__state == HOLDING:
            self.__cache.add_comment(comment)

    def empty_line(self):
        # print "A empty line is in"
        if self.__state == HEADER:
            # print "Current in header state, chaning to expecting_loggers"
            self.__state = EXPECTING_LOGGERS

    def new_line(self, line):
        # print "A new line come in [" + line + "]"
        if self.__state == EXPECTING_LOGGERS or self.__state == HEADER or self.__state == INIT:
            if not line.startswith("loggers="):
                self.__state = HOLDING
                self.new_line(line)
                return
            # it should be loggers line
            self.__context.add_loggers(line)
            self.__state = HOLDING
        elif self.__state == HOLDING:
            # print "The line is a prop line"
            name_with_prop = line.split(".", 1)[1]
            name_without_prop = name_with_prop.split("=", 1)[0]
            entry_name_split = name_without_prop.rsplit(".", 1)
            entry_name = ""
            if len(entry_name_split) > 1:
                entry_name = entry_name_split[0]
            # print "Got entry name: [" + entry_name + "]"
            # extract key and value
            keyvalue = line.split("=")
            self.__cache.set_keyvalue(keyvalue)
            # print "entry name: " + entry_name
            # print "key value: "

            if line.startswith("logger."):
                # loggers setting, what if root logger like logger.level?
                # print "setting logger prop for: " + entry_name
                # extract key and value
                self.__context.add_logger_config(entry_name, self.__cache)
                self.__cache.reset()
            elif line.startswith("handler."):
                # handlers setting: handler.[handler_name].prop=val
                if entry_name == "":
                    # special case handler.[handler_name]=val
                    entry_name = self.__cache.prop_key.split(".")[1]
                    # print "Special handler case, change entry name: [" + entry_name + "]"
                # print "setting handler prop for: " + entry_name
                self.__context.add_handler_config(entry_name, self.__cache)
                self.__cache.reset()
            elif line.startswith("formatter."):
                # formatters_setting: formatter.[formatter_name].prop=val
                if entry_name == "":
                    # special case formatter.[formatter_name]=val
                    entry_name = self.__cache.prop_key.split(".")[1]
                    # print "Special formatter case, change entry name: [" + entry_name + "]"
                # print "setting formater prop for: " + entry_name
                self.__context.add_formatter_config(entry_name, self.__cache)
                self.__cache.reset()
            else:
                print "!!!don't know what to do!!!"


class ParsingContext:

    def __init__(self):
        self.logging_properties = LoggingProperties()
        self.state = ParsingState(self)

    def feed_comment(self, comment):
        self.state.comment_in(comment)

    def feed_empty_line(self):
        self.state.empty_line()

    def feed_line(self, line):
        self.state.new_line(line)

    def add_loggers(self, loggers_string):
        self.logging_properties.add_loggers(loggers_string)

    def add_header_line(self, comment):
        self.logging_properties.add_header_line(comment)

    def add_logger_config(self, logger_name, entry):
        self.logging_properties.add_logger_config(logger_name, entry)

    def add_handler_config(self, handler_name, entry):
        self.logging_properties.add_handler_config(handler_name, entry)

    def add_formatter_config(self, formatter_name, entry):
        self.logging_properties.add_formatter_config(formatter_name, entry)

    def get_result(self):
        return self.logging_properties


class LoggingConfigManager:

    def __init__(self, **options):
        self._options = options

    # I'd like this parse method to return those values
    # 1. Header (license)
    # 2. LoggerNames
    # 3. []LoggerConfig
    # 4. []HandlerConfig
    # 5. []FormatterConfig
    # Even thou python allow multiple return values
    # I prefer wrapping it in a class
    def parse(self, cfg_file):
        file_handle = open(cfg_file, 'r')
        try:
            parsing_context = ParsingContext()
            # note: the line includes the newline char
            for line in file_handle:
                line = line.strip()
                # print "Parsing line: ===>[" + line + "]"
                if line.startswith("#"):
                    parsing_context.feed_comment(line)
                elif line in ['\n', '\r\n', '']:
                    parsing_context.feed_empty_line()
                else:
                    parsing_context.feed_line(line)
            return parsing_context.get_result()
        finally:
            file_handle.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merging logging.properties')
    parser.add_argument('--target', required=True, type=str, nargs=1,
                        help='The target logging properties file to merge into')
    parser.add_argument('--source', required=True, type=str, nargs=1,
                        help='The source logging properties file that will be merged into target')
    args = vars(parser.parse_args())
    source = args['source'][0]
    target = args['target'][0]
    print "source: " + source + " target: " + target
    manager = LoggingConfigManager()
    existing_cfg = manager.parse(target)
    new_cfg = manager.parse(source)
    print "===================================merging...."
    existing_cfg.merge(new_cfg, False)
    # new_cfg.write_to_file("result.logging.properties")
    existing_cfg.write_to_file(target)
    print "merge done"
