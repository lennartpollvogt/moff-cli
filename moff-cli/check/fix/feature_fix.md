---
project: moff-cli
feature: fix
linked_features: [check, settings]
---

# Overview

The option `--fix` can be used to automatically fix some issues when running the `check` command.

## Requirements

### Fix Possibility

When using the `check` command without `--fix` the result should contain the information about the fix possibilities.

Example with fix possibility:
```zsh
Discovering documentation root...
Collecting documentation files...
Root directory: /Users/lennartpollvogt/Documents/GitHub/moff-cli/moff-cli

Summary:
  Files checked: 13
  Total issues: 1
  Errors: 1
  Possible fixes: 1


Issues found:


moff-cli/check/fix/feature_fix.md:
  error  headers.missing: Missing required header level=1 text='Overview'
```

### Metadata

#### Missing Metadata

In case metadata is missing at all, the `--fix` option will add the metadata at the top of the file, based on the `settings.json` file.

For instance, for a `feature_*.md` file it was specified that the metadata should contain the following fields:
- `project`
- `feature`
- `linked_features`

Example for missing metadata:
```markdown
# Overview

## Requirements
```

Behavior of `--fix`:
```markdown
---
project:
feature:
linked_features: []
---

# Overview

## Requirements
```

Summary of behavior:
- should not replace existing text
- add the fields but with empty values
- in case of list add empty list (`[]`) to the field

#### Partially Missing Metadata

In case the metadata is incomplete, the `--fix` option will add the missing fields to the metadata element.

For instance, in the `settings.json` file it was specified that the metadata should contain the following fields:
- `project`
- `feature`
- `linked_features`

Example for partially missing metadata:
```markdown
---
project: moff-cli
feature: fix
---

# Overview

## Requirements
```

Behavior of `--fix`:
```markdown
---
project: moff-cli
feature: fix
linked_features: []
---

# Overview

## Requirements
```

Summary of behavior:
- should not replace existing text
- add the missing fields but with empty values
- in case of list add empty list (`[]`) to the field
- inserts in the correct position

### Headers

#### Missing Headers

In case headers are missing at all, the `--fix` option will add the headers at the correct position of the file, based on the `settings.json` file.

For isntance, in the `settings.json` file the specified markdown elements are:
- metadata
  - project
  - feature
  - linked_features
- headers
  - `# Overview`
  - `## Requirements`

Missing header example:
```markdown
---
project: moff-cli
feature: fix
linked_features: [check]
---

## Requirements
```

Behavior of `--fix`:
```markdown
---
project: moff-cli
feature: fix
linked_features: [check]
---

# Overview

## Requirements
```

#### Wrong Level

In case a header is existing but is having the wrong level, the `--fix` option will correct the level of the header.

For instance, in the `settings.json` file the specified markdown elements are:
- metadata
  - project
  - feature
  - linked_features
- headers
  - `# Overview`
  - `## Requirements`

Wrong level example:
```markdown
---
project: moff-cli
feature: fix
linked_features: [check]
---

# Overview

# Requirements
```

Behavior of `--fix`:
```markdown
---
project: moff-cli
feature: fix
linked_features: [check]
---

# Overview

## Requirements
```

### Interaction with Other Options

#### --save Option

When `--fix` is used together with `--save`, the behavior is:

1. **Initial diagnostics** are collected from the documentation
2. **Fixes are applied** to resolve fixable issues
3. **Re-validation** occurs to get the updated state
4. **`moff_results.txt` is saved with the remaining issues** (after fixes)

This means the saved results file will only contain:
- Unfixable issues (like location constraints)
- Issues that couldn't be automatically resolved
- Any new issues that might have been revealed after fixing

Example workflow:
```bash
# Check, fix, and save results in one command
moff check --fix --save

# The moff_results.txt will contain only the issues that remain after automatic fixes
```

This behavior ensures that:
- The results file reflects the current state of the documentation
- Users see what still needs manual attention
- There's no confusion about which issues have already been addressed
