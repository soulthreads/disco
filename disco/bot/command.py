import re

from disco.bot.parser import ArgumentSet, ArgumentError
from disco.util.functional import cached_property

REGEX_FMT = '({})'
ARGS_REGEX = '( (.*)$|$)'


class CommandEvent(object):
    """
    An event which is created when a command is triggered. Contains information
    about the message, command, and parsed arguments (along with shortcuts to
    message information).

    Attributes
    ---------
    command : :class:`Command`
        The command this event was created for (aka the triggered command).
    msg : :class:`disco.types.message.Message`
        The message object which triggered this command.
    match : :class:`re.MatchObject`
        The regex match object for the command.
    name : str
        The command name (or alias) which was triggered by the command
    args : list(str)
        Arguments passed to the command
    """

    def __init__(self, command, msg, match):
        self.command = command
        self.msg = msg
        self.match = match
        self.name = self.match.group(1)
        self.args = self.match.group(2).strip().split(' ')

    @cached_property
    def member(self):
        """
        Guild member (if relevant) for the user that created the message
        """
        return self.guild.get_member(self.author)

    @property
    def channel(self):
        """
        Channel the message was created in
        """
        return self.msg.channel

    @property
    def guild(self):
        """
        Guild (if relevant) the message was created in
        """
        return self.msg.guild

    @property
    def author(self):
        """
        Author of the message
        """
        return self.msg.author


class CommandError(Exception):
    """
    An exception which is thrown when the arguments for a command are invalid,
    or don't match the commands specifications.
    """


class Command(object):
    """
    An object which defines and handles the triggering of a function based on
    user input (aka a command).

    Attributes
    ----------
    plugin : :class:`disco.bot.plugin.Plugin`
        The plugin this command is a member of.
    func : function
        The function which is called when this command is triggered.
    trigger : str
        The primary trigger (aka name).
    args : Optional[str]
        The argument format specification.
    aliases : Optional[list(str)]
        List of trigger aliases.
    group : Optional[str]
        The group this command is a member of.
    is_regex : Optional[bool]
        Whether the triggers for this command should be treated as raw regex.
    """
    def __init__(self, plugin, func, trigger, args=None, aliases=None, group=None, is_regex=False):
        self.plugin = plugin
        self.func = func
        self.triggers = [trigger] + (aliases or [])

        self.args = ArgumentSet.from_string(args or '')
        self.group = group
        self.is_regex = is_regex

    @cached_property
    def compiled_regex(self):
        """
        A compiled version of this commands regex
        """
        return re.compile(self.regex)

    @property
    def regex(self):
        """
        The regex string that defines/triggers this command
        """
        if self.is_regex:
            return REGEX_FMT.format('|'.join(self.triggers))
        else:
            group = self.group + ' ' if self.group else ''
            return REGEX_FMT.format('|'.join(['^' + group + trigger for trigger in self.triggers]) + ARGS_REGEX)

    def execute(self, event):
        """
        Handles the execution of this command given a :class:`CommandEvent`
        object.

        Returns
        -------
        bool
            Whether this command was sucessful
        """
        if len(event.args) < self.args.required_length:
            raise CommandError('{} requires {} arguments (passed {})'.format(
                event.name,
                self.args.required_length,
                len(event.args)
            ))

        try:
            args = self.args.parse(event.args)
        except ArgumentError as e:
            raise CommandError(e.message)

        return self.func(event, *args)