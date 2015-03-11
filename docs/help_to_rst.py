#!/usr/bin/env python

import re
import sys

output_lines = []
in_synopsis = False
in_description = False
in_options = False
in_examples = False
for line in sys.stdin:
    if re.match("^usage:", line):
        output_lines.append("Synopsis")
        output_lines.append("--------")
        output_lines.append("::")
        output_lines.append("")
        in_synopsis = True
        continue
    elif in_synopsis and not re.match("^  ", line):
        output_lines.append("")
        output_lines.append("Description")
        output_lines.append("-----------")
        in_synopsis = False
        in_description = True
    elif in_description and not re.match("^\S", line):
        output_lines.append("")
        output_lines.append("Options")
        output_lines.append("-------")
        in_description = False
        in_options = True
    elif in_options and re.match("^Example", line):
        # Entering the (optional) examples epilog
        output_lines.append("Examples")
        output_lines.append("--------")
        output_lines.append("")
        in_options = False
        in_examples = True
        continue
    elif in_options and re.match("^\S", line):
        # Options subsection - strip trailing ':'
        label = line.rstrip()[:-1]
        output_lines.append(label)
        output_lines.append("*" * len(label))
        continue
    elif in_options and re.match("^  \S", line):
        # New argument
        # Do we have any trailing text?
        match = re.match("^  (.*\S)  +(\S.*)", line)
        if match:
            output_lines.append(match.group(1).strip())
            line = "  " + (match.group(2).strip())
        else:
            line = line.strip()
        # RST is picky about what an option's values look like

        # --type {e1000,virtio}   ---->   --type <e1000,virtio>
        line = re.sub(r"(-+\S+) {([^}]+)}", r"\1 <\2>", line)

        # --names NAME1 [NAME2 ...] ---->  --names <NAME1 ...>
        line = re.sub(r"(-+\S+) ([^,]+) \[[^,]+\]",
                      r"\1 <\2...>", line)
    elif in_options and re.match("^        ", line):
        # Description of an option - keep it under the option_list
        line = "  " + line.strip()
    elif in_examples and re.match("^  \S", line):
        # Beginning of an example - mark as a literal
        output_lines.append("::")
        output_lines.append("")
    elif in_examples and re.match("^    \S", line):
        # Description of an example - exit any literal block
        if re.match("^  ", output_lines[-1]):
            output_lines.append("")
        line = line.strip()
    else:
        pass
    output_lines.append(line.rstrip())

print("\n".join(output_lines))
