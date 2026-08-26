---
layout: post
title: "AD & M365 Onboarding Automation: A WPF PowerShell GUI for New User Provisioning"
date: 2026-08-26
excerpt: "A look at a WPF-based PowerShell onboarding tool that creates Active Directory users, waits for Entra ID sync, and assigns Microsoft 365 licenses without turning every new hire into a checklist marathon."
og_image: /assets/og/ad-m365-onboarding-automation.png
og_slug: ad-m365-onboarding-automation
image:
  path: /assets/og/ad-m365-onboarding-automation.png
  width: 1200
  height: 630
  alt: AD and Microsoft 365 onboarding automation branded social preview image
tags:
  - PowerShell
  - Active Directory
  - Microsoft 365
  - Automation
  - Homelab
---

New user onboarding is one of those IT tasks that looks simple until you count how many tiny ways there are to screw it up.

Create the AD account. Put it in the right OU. Set the username and UPN correctly. Add phone, title, department, office, company, description, maybe a manager. Wait for AD Connect to drag the object into Entra ID. Find the synced cloud user. Set `UsageLocation`. Pick a Microsoft 365 license that actually has capacity. Assign it. Log enough detail that future-you can figure out what happened when someone asks why the mailbox isn't ready yet.

None of that is hard. That's the problem. It's repetitive, easy to rush, and exactly the sort of thing that becomes tribal knowledge living in an admin's head until the admin takes PTO and everyone discovers the onboarding process was actually a human API.

So I built a WPF PowerShell GUI for it.

The script is `NewUserProvisioningGUI.ps1`, and the public version is sanitized: placeholder organization name, placeholder UPN suffix, placeholder OU distinguished names, and no production credentials or private OU structure. The logic is still the useful part.

## 1. The problem it solves

The script is trying to collapse the usual AD-plus-Microsoft-365 onboarding path into one operator flow.

Before automation, this sort of workflow usually means bouncing between tools: Active Directory Users and Computers, whatever notes or naming convention document exists this week, Azure/Entra admin portals, Microsoft 365 licensing screens, and a terminal window for the parts nobody bothered to put in a runbook.

This script pulls the operator-facing inputs into one form and then runs the backend steps in order:

- create the on-prem AD user
- enable the account
- optionally set common profile attributes
- optionally set a manager
- wait for AD Connect sync
- connect to Microsoft Graph
- poll for the synced Entra ID user
- set `UsageLocation` to `US`
- discover available subscribed SKUs
- pick or prompt for a license
- assign the license
- write a timestamped log under `.\Logs`

That last part matters. If the tool fails halfway through, it doesn't just vanish into the same abyss as Teams presence accuracy. It logs the step it was on and the exception it hit.

## 2. Why a GUI instead of another console script

The script's own header says the WPF form replaces `Read-Host` prompts. That's the clearest design reason in the file: this is meant to be operated as a form, not as a question-by-question console interrogation.

The UI exposes the fields an operator actually needs during onboarding:

- first name
- last name
- username
- initial password
- optional email
- optional telephone
- optional job title
- optional department
- optional company
- optional office
- optional description
- target OU
- optional manager search
- license assignment mode

It also includes a live progress log and a status label, so the operator can see whether the tool is creating the AD user, waiting for sync, polling Entra ID, connecting to Graph, or assigning the license.

The script does not auto-generate usernames. The username field is explicit and required, with the UI hint `e.g. jdoe`. That is a useful boundary: the tool automates provisioning, but it does not pretend to own the naming policy.

## 3. What it automates, in the order the code runs

The script starts with an elevation check. If it is not running as Administrator, it relaunches itself with:

```powershell
-NoProfile -STA -ExecutionPolicy Bypass -File "$PSCommandPath"
```

The `-STA` part matters because WPF expects a single-threaded apartment. Skip that and you get the sort of GUI weirdness that makes people decide PowerShell is haunted.

After loading WPF assemblies, the script sets configuration values:

```powershell
$PreferredSkuOrder              = @('SPE_E3','ENTERPRISEPACK')
$InitialSyncWaitSeconds         = 300
$UserDiscoveryRetryCount        = 60
$UserDiscoveryRetryDelaySeconds = 30
$LogRetentionDays               = 90
$UPNSuffix                      = "@<UPN_SUFFIX>"
```

It creates a `Logs` directory next to the script, removes old `.log` and `.txt` files older than 90 days, and creates a timestamped log file named like:

```text
NewUserProvisioning_yyyyMMdd_HHmmss.log
```

Then it builds the OU dropdown from a static `$OUs` array. The public script uses `<OU_DISTINGUISHED_NAME_1>` through `<OU_DISTINGUISHED_NAME_17>` placeholders. The helper `Get-OUFriendlyName` splits the distinguished name, keeps `OU=` components, strips the prefix, and joins them with ` > ` for display.

When the operator clicks **Provision User**, the script validates only the required fields:

- first name
- last name
- username
- password
- selected OU

Then it calculates:

```powershell
$UPN = "$Username$UPNSuffix"
```

The actual provisioning work runs inside a separate PowerShell runspace. The form disables the Provision button, changes status to `Provisioning...`, clears the live log, passes all collected values into the runspace, and starts it asynchronously with `BeginInvoke()`.

Inside the runspace, the order is straightforward:

1. Import `ActiveDirectory` with `-ErrorAction Stop`.
2. Convert the entered password with `ConvertTo-SecureString -AsPlainText -Force`.
3. Build a `New-ADUser` splat with required identity fields.
4. Add optional attributes only if the operator filled them in.
5. Add `Manager` only if a manager was selected.
6. Run `New-ADUser @splat -PassThru | Enable-ADAccount`.
7. Wait 300 seconds for AD Connect sync, updating the status label every 5 seconds.
8. Connect to Microsoft Graph with `User.ReadWrite.All,Directory.ReadWrite.All`.
9. Poll `Get-MgUser -UserId $UPN` up to 60 times, sleeping 30 seconds between attempts.
10. Throw if the user never appears in Entra ID.
11. Run `Set-MgUser -UserId $UPN -UsageLocation "US"`.
12. Pull subscribed SKUs with `Get-MgSubscribedSku`.
13. Select a license.
14. Assign it with `Set-MgUserLicense`.

That is the actual flow. There is no group assignment in the current script. There is no mailbox policy logic. There is no username generator. There is no AD duplicate pre-check before `New-ADUser`. If those happen elsewhere in an environment, they are not in this file. Documentation should not hallucinate features just because they would be nice.

## 4. How the UI and automation logic are structured

Everything lives in one `.ps1` file.

The XAML is embedded directly in a here-string and loaded with:

```powershell
$Reader = New-Object System.Xml.XmlNodeReader $XAML
$Window = [Windows.Markup.XamlReader]::Load($Reader)
```

After that, the script calls `$Window.FindName(...)` for each control and stores references like `$txtFirstName`, `$pwdPassword`, `$cboOU`, `$txtManagerSearch`, `$lstManagerResults`, `$cboLicense`, `$txtLog`, `$btnProvision`, and `$lblStatus`.

The UI layer handles three main events:

- manager search button click
- manager result selection
- provision button click

The backend automation is embedded in the script block passed to `$ps.AddScript({ ... })`. It defines two helper functions inside the runspace:

- `AppendLog` — writes timestamped log lines to disk and appends colored lines to the WPF log window through `$Window.Dispatcher.Invoke(...)`
- `SetStatus` — updates the status label through the dispatcher

That dispatcher usage is important. The provisioning work is running in another runspace, and WPF controls belong to the UI thread. The script updates the UI through the dispatcher instead of poking controls from the wrong thread like a gremlin with admin rights.

## 5. Real design decisions visible in the code

A few choices are obvious from the implementation.

Manager lookup is interactive. The search box runs:

```powershell
Get-ADUser -Filter "Name -like '*$escaped*'" -Properties SamAccountName, UserPrincipalName -ErrorAction Stop
```

Results are sorted by name, capped at 30, and displayed as `Name (SamAccountName)`. Selecting a result stores the user's `DistinguishedName` in `$script:SelectedManagerDN`; later, if that value exists, it becomes `$splat.Manager` for `New-ADUser`.

OU selection is static. The script does not query AD for available OUs at runtime. It expects the admin to replace the placeholder `$OUs` list with real distinguished names for the environment. That makes the UI predictable, but it also means OU maintenance is a code/config update, not discovery.

License selection has two modes. The default combo box option is auto-assignment, using:

```powershell
$PreferredSkuOrder = @('SPE_E3','ENTERPRISEPACK')
```

The script queries `Get-MgSubscribedSku`, calculates available seats as `PrepaidUnits.Enabled - ConsumedUnits`, and picks the first preferred SKU with availability. If auto mode is disabled, it builds a list of available SKUs, shows them in a message box, and assigns the first available SKU only if the operator clicks OK. It is not a full license picker. It is closer to a guarded prompt.

Usage location is hardcoded to `US`. That may be correct for the intended environment, but it is a real design constraint in the script as written.

Username generation is not automated. The operator types `$Username`, and the script builds `$UPN` by appending `$UPNSuffix`. That keeps the script simple, but it means naming collision checks depend on `New-ADUser` failing or on a process outside the script.

## 6. Actual error handling

The script uses a mix of UI validation, `try/catch`, and explicit `throw` statements.

Before provisioning starts, it validates required UI fields and shows a WPF message box if anything is missing. Manager search also validates that a search term exists before querying AD.

The manager lookup catches AD search failures and shows:

```text
AD search failed: <exception message>
```

The provisioning runspace sets:

```powershell
$ErrorActionPreference = 'Stop'
```

Then the main provisioning workflow is wrapped in `try/catch/finally`. Failures are logged through:

```powershell
AppendLog ERROR "Provisioning FAILED: $($_.Exception.Message)"
```

The script explicitly throws for several conditions:

- the synced Entra ID user is not found after the polling timeout
- no preferred M365/O365 E3 SKU is available in auto-license mode
- no licenses are available in manual mode
- the operator cancels license assignment

In `finally`, the UI is put back into an operable state: the Provision button is re-enabled, and the status label becomes either `Provisioning complete!` or `Provisioning failed - see log above.`

There are also a couple of quieter catches. Log cleanup errors are ignored. Manager search errors are shown to the user. Polling for the Entra user logs retry warnings rather than failing immediately. That is a reasonable distinction: cleanup failure should not block onboarding, AD search failure should be visible, and Entra sync delay is expected enough to retry.

## 7. Closing

This is the kind of PowerShell script I like: it does not try to become an identity platform. It wraps the boring, failure-prone onboarding path in a form, runs the AD and Graph steps in a predictable order, and keeps the operator informed while Microsoft cloud sync takes its sweet time.

The public version still needs environment-specific placeholders filled in before anyone should run it: UPN suffix, OU distinguished names, organization label, and the usual module/auth prerequisites. It also leaves some deliberate gaps — no username generation, no group assignment, no duplicate-user preflight, no full SKU picker. Those are not bugs unless you expected them to be there.

What it does automate is the part that usually burns time: create the AD account, wait for the cloud object, set the cloud-side requirement, and license the user with enough logging to prove what happened.

That is not glamorous. It is onboarding. Glamour would be suspicious.

Script: [User-Provisioning/NewUserProvisioningGUI.ps1](https://github.com/mdziegiel/powershell-scripts/blob/main/User-Provisioning/NewUserProvisioningGUI.ps1)
