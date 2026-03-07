/**
 * English (US) locale -- base language file.
 *
 * Every user-facing string in the app lives here. Each entry has:
 *  - text:    The display string. Supports ICU MessageFormat syntax for
 *             interpolation ({name}) and plurals ({count, plural, one {# item} other {# items}}).
 *  - context: Description of where/why this string appears. Used by the
 *             AI translation agent to produce natural translations.
 */

export interface LocaleEntry {
  text: string
  context: string
}

const en_US: Record<string, LocaleEntry> = {
  // ══════════════════════════════════════════════════════════════════════
  // Navigation
  // ══════════════════════════════════════════════════════════════════════
  'nav.dashboard': {
    text: 'Dashboard',
    context: 'Top navigation tab. Takes the user to the main overview page showing balance, upcoming bills, and cash flow trajectory.',
  },
  'nav.commitments': {
    text: 'Commitments',
    context: 'Top navigation tab. Takes the user to the page where they manage recurring expenses, income, and one-time payments.',
  },
  'nav.simulation': {
    text: 'Simulation',
    context: 'Top navigation tab. Takes the user to the what-if scenario playground for toggling commitments and projecting outcomes.',
  },
  'nav.logout': {
    text: 'Logout',
    context: 'Button in the top navigation bar that signs the user out of their session.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Login page
  // ══════════════════════════════════════════════════════════════════════
  'login.brand': {
    text: 'Athena',
    context: 'Application name displayed prominently on the login page.',
  },
  'login.version': {
    text: 'v1',
    context: 'Version label shown next to the app name on the login page.',
  },
  'login.tagline': {
    text: 'Cash flow projection and financial awareness.',
    context: 'One-line description of the app shown below the brand name on the login page.',
  },
  'login.sign_in': {
    text: 'Sign in with Discord',
    context: 'Primary login button that redirects to Discord OAuth2 authentication.',
  },
  'login.demo': {
    text: 'Try Demo',
    context: 'Secondary button on the login page that launches a demo session without an account.',
  },
  'login.demo_sub': {
    text: 'No account required',
    context: 'Small text below the demo button explaining that no sign-up is needed.',
  },
  'login.secure': {
    text: 'Secure session via OAuth 2.0',
    context: 'Footer text on the login page reassuring users about security.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Dashboard
  // ══════════════════════════════════════════════════════════════════════
  'dash.bills_this_week': {
    text: 'Bills This Week',
    context: 'Section header on the dashboard above the list of bills due in the current week.',
  },
  'dash.resets': {
    text: 'resets {date}',
    context: 'Small label next to "Bills This Week" showing when the week resets. {date} is a formatted date like "Mon Feb 24".',
  },
  'dash.loading': {
    text: 'Loading projection...',
    context: 'Placeholder message shown while the dashboard data is being fetched from the server.',
  },
  'dash.no_data_title': {
    text: 'No projection data',
    context: 'Heading shown on the dashboard when there is no projection data to display.',
  },
  'dash.no_data_desc': {
    text: 'Add commitments to see your cash flow trajectory.',
    context: 'Instructional text shown below "No projection data" when the user has no commitments yet.',
  },

  // Dashboard Hero
  'hero.current_balance': {
    text: 'Current Balance',
    context: 'Label below the large balance number at the top of the dashboard.',
  },
  'hero.save': {
    text: 'Save',
    context: 'Button that confirms the inline balance edit on the dashboard hero.',
  },
  'hero.esc': {
    text: 'Esc',
    context: 'Label indicating the Escape key cancels the inline balance edit.',
  },
  'hero.critical': {
    text: 'Critical',
    context: 'Financial health verdict when the projected lowest balance goes negative. Shown in the shield gauge.',
  },
  'hero.tight': {
    text: 'Tight',
    context: 'Financial health verdict when the projected lowest balance is low but positive. Shown in the shield gauge.',
  },
  'hero.comfortable': {
    text: 'Comfortable',
    context: 'Financial health verdict when the projected lowest balance is healthy. Shown in the shield gauge.',
  },
  'hero.days_projected': {
    text: '{count} days projected',
    context: 'Shows how many days the projection covers. Appears next to the shield gauge. {count} is a number like 90.',
  },
  'hero.after_window': {
    text: 'After Window',
    context: 'Label for the stat showing the projected balance at the end of the projection window.',
  },
  'hero.lowest_point': {
    text: 'Lowest Point',
    context: 'Label for the stat showing the lowest projected balance within the window.',
  },
  'hero.net_change': {
    text: 'Net Change',
    context: 'Label for the stat showing the total gain or loss over the projection window.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Bills This Week panel
  // ══════════════════════════════════════════════════════════════════════
  'bills.empty': {
    text: 'No bills due for the rest of this week',
    context: 'Shown in the bills panel when there are no upcoming bills this week.',
  },
  'bills.total': {
    text: 'Total',
    context: 'Label in the bills panel footer next to the summed total of this week\'s bills.',
  },
  'bills.next_week': {
    text: 'Next week -- {amount} in bills',
    context: 'Summary line showing next week\'s total bills. {amount} is a formatted currency value like "$1,234".',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Cause Panel (tightest pay period)
  // ══════════════════════════════════════════════════════════════════════
  'cause.title': {
    text: 'Your tightest pay period',
    context: 'Header of the cause panel that breaks down the pay period with the most expense pressure.',
  },
  'cause.total': {
    text: '{amount} total',
    context: 'Shows the total expenses in the tightest pay period. {amount} is a formatted currency value.',
  },
  'cause.window_range': {
    text: 'Tightest window: {range}',
    context: 'Subheading showing the date range of the tightest pay period. {range} is like "Feb 1 - Feb 14".',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Shortfall Warning
  // ══════════════════════════════════════════════════════════════════════
  'shortfall.goes_negative': {
    text: 'Balance goes negative {date}',
    context: 'Warning headline when the projection shows the balance dropping below zero. {date} is a short date like "Mar 5".',
  },
  'shortfall.projected': {
    text: 'Projected {amount} shortfall',
    context: 'Shows the projected negative balance amount. {amount} is a formatted currency value.',
  },
  'shortfall.recovery': {
    text: '-- next paycheck {date}',
    context: 'Appended to the shortfall line when a recovery date (next income) is known. {date} is a short date. Uses a dash separator.',
  },
  'shortfall.at_risk': {
    text: '{count, plural, one {# commitment at risk} other {# commitments at risk}}',
    context: 'Footer of the shortfall warning showing how many commitments may be missed due to insufficient funds.',
  },
  'shortfall.total': {
    text: '-{amount} total',
    context: 'Total amount of missed commitments in the shortfall warning. {amount} is a formatted currency value.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Trajectory Chart
  // ══════════════════════════════════════════════════════════════════════
  'chart.title': {
    text: 'Balance Trajectory',
    context: 'Section header above the main cash flow line chart on the dashboard.',
  },
  'chart.hover_hint': {
    text: 'hover chart to inspect',
    context: 'Placeholder text in the info bar above the chart, shown when the user is not hovering over any data point.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Event List
  // ══════════════════════════════════════════════════════════════════════
  'events.title': {
    text: 'Upcoming Events',
    context: 'Section header above the chronological list of projected income and expense events.',
  },
  'events.count': {
    text: '{count} events',
    context: 'Badge next to the events title showing the total number of projected events. {count} is a number.',
  },
  'events.col_day': {
    text: 'Day',
    context: 'Column header in the events table for the day of the event.',
  },
  'events.col_name': {
    text: 'Name',
    context: 'Column header in the events table for the event name.',
  },
  'events.col_amount': {
    text: 'Amount',
    context: 'Column header in the events table for the event amount.',
  },
  'events.col_balance': {
    text: 'Balance',
    context: 'Column header in the events table for the running balance after the event.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Paycheck Bands
  // ══════════════════════════════════════════════════════════════════════
  'bands.spent': {
    text: 'Spent {amount}',
    context: 'Shows total spending within a pay period band. {amount} is a formatted currency value.',
  },
  'bands.min': {
    text: 'Min {amount}',
    context: 'Shows the minimum balance within a pay period band. {amount} is a formatted currency value.',
  },
  'bands.partial': {
    text: '(partial)',
    context: 'Tag shown next to a pay period that is not yet complete (the end date is in the future).',
  },
  'bands.start': {
    text: 'Start',
    context: 'Label for the starting balance of a pay period.',
  },
  'bands.end': {
    text: 'End',
    context: 'Label for the ending balance of a pay period.',
  },
  'bands.net': {
    text: 'Net',
    context: 'Label for the net gain/loss within a pay period.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Commitments page
  // ══════════════════════════════════════════════════════════════════════
  'commit.page_title': {
    text: 'Commitments',
    context: 'Page heading on the commitments management page.',
  },
  'commit.page_desc': {
    text: 'Manage recurring expenses, income, and one-time payments that drive your trajectory.',
    context: 'Subtitle below the commitments page heading explaining the purpose of the page.',
  },
  'commit.monthly_income': {
    text: 'Monthly Income',
    context: 'Label on the summary card showing total monthly income from recurring commitments.',
  },
  'commit.monthly_expenses': {
    text: 'Monthly Expenses',
    context: 'Label on the summary card showing total monthly expenses from recurring commitments.',
  },
  'commit.net_per_month': {
    text: 'Net / Month',
    context: 'Label on the summary card showing the net monthly cash flow (income minus expenses).',
  },
  'commit.total_items': {
    text: 'Total Items',
    context: 'Label on the summary card showing the total number of commitments.',
  },
  'commit.add': {
    text: 'Add Commitment',
    context: 'Button that opens the modal to create a new commitment.',
  },
  'commit.loading': {
    text: 'Loading commitments...',
    context: 'Placeholder message shown while commitments are being fetched from the server.',
  },
  'commit.col_name': {
    text: 'Name',
    context: 'Column header in the commitments table for the commitment name.',
  },
  'commit.col_amount': {
    text: 'Amount',
    context: 'Column header in the commitments table for the commitment amount.',
  },
  'commit.col_freq': {
    text: 'Frequency',
    context: 'Column header in the commitments table for how often the commitment recurs.',
  },
  'commit.col_next': {
    text: 'Next',
    context: 'Column header in the commitments table for the next occurrence date.',
  },
  'commit.per_month': {
    text: '/mo',
    context: 'Suffix appended to monetary values to indicate "per month". Shown on category totals and scenario breakdowns.',
  },
  'commit.one_time_title': {
    text: 'One-Time Payments ({count})',
    context: 'Section header for one-time payments. {count} is the number of one-time items.',
  },
  'commit.total': {
    text: '{amount} total',
    context: 'Shows the total amount of one-time payments. {amount} is a formatted currency value.',
  },
  'commit.col_date': {
    text: 'Date',
    context: 'Column header in the one-time payments table for the payment date.',
  },
  'commit.remove': {
    text: 'Remove',
    context: 'Tooltip on the delete button for a commitment row.',
  },
  'commit.group_income': {
    text: 'Income',
    context: 'Group label for the income section in the commitments list.',
  },
  'commit.group_expenses': {
    text: 'Expenses',
    context: 'Group label for the expense section in the commitments list.',
  },

  // Frequency labels
  'freq.monthly': {
    text: 'Monthly',
    context: 'Human-readable label for a commitment that recurs every month.',
  },
  'freq.biweekly': {
    text: 'Biweekly',
    context: 'Human-readable label for a commitment that recurs every two weeks.',
  },
  'freq.weekly': {
    text: 'Weekly',
    context: 'Human-readable label for a commitment that recurs every week.',
  },
  'freq.daily': {
    text: 'Daily',
    context: 'Human-readable label for a commitment that recurs every day.',
  },
  'freq.custom': {
    text: 'Custom',
    context: 'Human-readable label for a commitment with a custom day interval.',
  },
  'freq.once': {
    text: 'One-Time',
    context: 'Human-readable label for a commitment that occurs only once.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Commitment Modal
  // ══════════════════════════════════════════════════════════════════════
  'modal.add_title': {
    text: 'Add Commitment',
    context: 'Title of the modal dialog when creating a new commitment.',
  },
  'modal.edit_title': {
    text: 'Edit Commitment',
    context: 'Title of the modal dialog when editing an existing commitment.',
  },
  'modal.name': {
    text: 'Name',
    context: 'Field label for the commitment name in the add/edit modal.',
  },
  'modal.name_placeholder': {
    text: 'e.g. Netflix, Car Payment',
    context: 'Placeholder text in the name input field of the commitment modal.',
  },
  'modal.amount': {
    text: 'Amount ({symbol})',
    context: 'Field label for the commitment amount. {symbol} is the currency symbol like "$" or "Won".',
  },
  'modal.type': {
    text: 'Type',
    context: 'Field label for the commitment type selector (expense or income).',
  },
  'modal.type_expense': {
    text: 'Expense',
    context: 'Option in the type dropdown for a commitment that costs money.',
  },
  'modal.type_income': {
    text: 'Income',
    context: 'Option in the type dropdown for a commitment that brings in money.',
  },
  'modal.frequency': {
    text: 'Frequency',
    context: 'Field label for the commitment frequency selector.',
  },
  'modal.day_of_month': {
    text: 'Day of Month',
    context: 'Field label for which day of the month a monthly commitment occurs.',
  },
  'modal.date': {
    text: 'Date',
    context: 'Field label for the date of a one-time payment.',
  },
  'modal.starting_from': {
    text: 'Starting From',
    context: 'Field label for the anchor date of biweekly or weekly commitments.',
  },
  'modal.start_date': {
    text: 'Start Date',
    context: 'Field label for when a recurring commitment begins.',
  },
  'modal.cancel': {
    text: 'Cancel',
    context: 'Button in the commitment modal that closes it without saving.',
  },
  'modal.saving': {
    text: 'Saving...',
    context: 'Button label shown while the commitment is being saved to the server.',
  },
  'modal.save': {
    text: 'Save',
    context: 'Button that confirms and saves the commitment.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Simulation page
  // ══════════════════════════════════════════════════════════════════════
  'sim.running': {
    text: 'Running simulation...',
    context: 'Loading message shown while the simulation projection is being calculated.',
  },
  'sim.current': {
    text: 'Current',
    context: 'Label for the card showing the current balance in the simulation results strip.',
  },
  'sim.after_window': {
    text: 'After Window',
    context: 'Label for the card showing the projected balance at the end of the simulation window.',
  },
  'sim.lowest_point': {
    text: 'Lowest Point',
    context: 'Label for the card showing the lowest projected balance during the simulation window.',
  },
  'sim.avg_gained': {
    text: 'Avg Gained / Month',
    context: 'Label for the card showing the average monthly gain or loss in the simulation.',
  },
  'sim.monthly_breakdown': {
    text: 'Monthly Breakdown',
    context: 'Section header for the month-by-month breakdown of the simulation results.',
  },
  'sim.months_count': {
    text: '{count} months',
    context: 'Badge showing how many months are covered in the simulation breakdown. {count} is a number.',
  },
  'sim.no_data_title': {
    text: 'No Data',
    context: 'Heading shown when the simulation produces no projection data.',
  },
  'sim.no_data_desc': {
    text: 'No projection data returned for the selected window. Check your commitments and balance.',
    context: 'Explanatory text shown when the simulation returns empty results.',
  },
  'sim.summary_title': {
    text: 'Scenario Summary',
    context: 'Title of the sticky sidebar panel showing the current scenario configuration.',
  },
  'sim.start_date': {
    text: 'Start Date',
    context: 'Label for the simulation start date picker.',
  },
  'sim.end_date': {
    text: 'End Date',
    context: 'Label for the simulation end date picker.',
  },
  'sim.net_per_month': {
    text: 'Simulated Net / Month',
    context: 'Label below the large net number in the scenario summary panel.',
  },
  'sim.income': {
    text: 'Income',
    context: 'Line item label in the scenario summary showing total monthly income.',
  },
  'sim.expenses': {
    text: 'Expenses',
    context: 'Line item label in the scenario summary showing total monthly expenses.',
  },
  'sim.active_items': {
    text: 'Active Items',
    context: 'Line item label showing how many commitments are active in the current scenario.',
  },
  'sim.savings_from_cuts': {
    text: 'Savings from Cuts',
    context: 'Line item label showing monthly savings from commitments the user disabled in the scenario.',
  },
  'sim.disabled_count': {
    text: '{count} disabled',
    context: 'Change note in the scenario summary showing how many commitments were toggled off. {count} is a number.',
  },
  'sim.edited_count': {
    text: '{count} edited',
    context: 'Change note in the scenario summary showing how many commitment amounts were modified. {count} is a number.',
  },
  'sim.reset': {
    text: 'Reset',
    context: 'Link in the scenario summary that resets all overrides back to original values.',
  },
  'sim.run_button': {
    text: 'Run Simulation',
    context: 'Primary action button that triggers the scenario projection calculation.',
  },
  'sim.running_button': {
    text: 'Running...',
    context: 'Button label shown while the simulation is being calculated.',
  },
  'sim.day_window': {
    text: '{count} day window',
    context: 'Small note below the Run button showing the number of days in the simulation window. {count} is a number.',
  },
  'sim.configure_title': {
    text: 'Configure & Run',
    context: 'Heading for the pre-run placeholder shown before the user runs their first simulation.',
  },
  'sim.configure_desc': {
    text: 'Toggle commitments, adjust amounts, then click "Run Simulation" to project your cash flow.',
    context: 'Instructional text shown before the first simulation run.',
  },

  // Scenario Commitments panel
  'scenario.income': {
    text: 'Income ({count})',
    context: 'Section header in the scenario commitment rails for income items. {count} is the number of income commitments.',
  },
  'scenario.expenses': {
    text: 'Expenses ({count})',
    context: 'Section header in the scenario commitment rails for expense items. {count} is the number of expense commitments.',
  },
  'scenario.one_time': {
    text: 'One-Time ({count})',
    context: 'Section header in the scenario commitment rails for one-time items. {count} is the number of one-time commitments.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Currency Prompt (initial setup)
  // ══════════════════════════════════════════════════════════════════════
  'currency_prompt.title': {
    text: 'Set Your Currency',
    context: 'Title of the modal shown on first login asking the user to choose their account currency.',
  },
  'currency_prompt.desc': {
    text: 'Choose your account currency. All amounts will be stored and displayed in this currency.',
    context: 'Description text in the currency setup modal explaining the implications of the choice.',
  },
  'currency_prompt.continue': {
    text: 'Continue',
    context: 'Confirm button in the currency setup modal.',
  },
  'currency_prompt.saving': {
    text: 'Saving...',
    context: 'Button label while the currency choice is being saved.',
  },
  'currency_prompt.lang_info': {
    text: 'Your default language will be set to',
    context: 'Info text shown below the currency grid. Followed by a clickable language name.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Currency Explainer (one-time popup)
  // ══════════════════════════════════════════════════════════════════════
  'explainer.title': {
    text: 'Display Currency',
    context: 'Title of the one-time popup that explains display currency conversion and rounding.',
  },
  'explainer.body': {
    text: 'Your account stores all amounts in {accountCurrency}. When you toggle to {displayCurrency}, values are converted at the current exchange rate. Small rounding differences are normal.',
    context: 'Main explanation in the currency explainer popup. {accountCurrency} is like "USD ($)" and {displayCurrency} is like "KRW (Won)".',
  },
  'explainer.you_enter': {
    text: 'You enter',
    context: 'Label for step 1 in the animated round-trip conversion graphic.',
  },
  'explainer.stored_as': {
    text: 'stored as',
    context: 'Arrow label between step 1 and step 2 in the conversion graphic, indicating the value is saved in account currency.',
  },
  'explainer.saved': {
    text: 'Saved',
    context: 'Label for step 2 in the conversion graphic showing the stored account-currency value.',
  },
  'explainer.displayed_as': {
    text: 'displayed as',
    context: 'Arrow label between step 2 and step 3 in the conversion graphic, indicating the value is converted back for display.',
  },
  'explainer.you_see': {
    text: 'You see',
    context: 'Label for step 3 in the conversion graphic showing the final displayed value after round-trip conversion.',
  },
  'explainer.difference': {
    text: '{delta} difference',
    context: 'Shows the rounding delta in the conversion graphic. {delta} is a signed number like "+28" or "-0.01".',
  },
  'explainer.dismiss': {
    text: 'Got it',
    context: 'Button that dismisses the currency explainer popup.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // ══════════════════════════════════════════════════════════════════════
  // First-Time Experience (FTE)
  // ══════════════════════════════════════════════════════════════════════
  'fte.welcome_title': {
    text: 'Welcome to Athena',
    context: 'Heading on the FTE welcome screen shown before the first tour starts.',
  },
  'fte.welcome_desc': {
    text: 'We will walk you through each section with sample data so you can see how everything works.',
    context: 'Description on the FTE welcome screen.',
  },
  'fte.welcome_hint': {
    text: 'Click the glowing Dashboard tab above to begin.',
    context: 'Hint text nudging the user to click the glowing tab.',
  },
  'fte.skip_tour': {
    text: 'Skip Tour',
    context: 'Button label in the NavBar to skip the entire FTE.',
  },
  'fte.complete_title': {
    text: 'You are all set!',
    context: 'Heading on the completion dialog shown after all tours finish.',
  },
  'fte.complete_desc': {
    text: 'Time to set up your real data and take control of your finances.',
    context: 'Description on the FTE completion dialog.',
  },
  'fte.complete_button': {
    text: 'Go to Dashboard',
    context: 'Button label on the completion dialog to finish FTE and load real data.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Guided Tours
  // ══════════════════════════════════════════════════════════════════════
  'tour.balance_title': {
    text: 'Your Balance at a Glance',
    context: 'Tour step title for the balance display on the dashboard.',
  },
  'tour.balance_desc': {
    text: 'This is your real bank balance. Tap it anytime to update -- everything recalculates instantly.',
    context: 'Tour step description explaining the editable balance on the dashboard.',
  },
  'tour.gauge_title': {
    text: 'Financial Health Shield',
    context: 'Tour step title for the shield gauge showing financial health status.',
  },
  'tour.gauge_desc': {
    text: 'Green means you are cruising. Yellow means things are tight. Red means action needed. This gauge looks 90 days ahead so you are never surprised.',
    context: 'Tour step description explaining the three-zone shield gauge colors and their meaning.',
  },
  'tour.bills_title': {
    text: 'Bills Coming Up',
    context: 'Tour step title for the bills-this-week section.',
  },
  'tour.bills_desc': {
    text: 'See exactly what is due this week and next. No more scrambling to remember which bills hit when.',
    context: 'Tour step description for the weekly bills breakdown.',
  },
  'tour.trajectory_title': {
    text: 'Your Cash Trajectory',
    context: 'Tour step title for the main balance trajectory chart.',
  },
  'tour.trajectory_desc': {
    text: 'A day-by-day map of your money for the next 90 days. Hover any point to see exactly what happens and when. The dips show you where to watch out.',
    context: 'Tour step description explaining the interactive trajectory chart.',
  },
  'tour.cause_title': {
    text: 'What Is Eating Your Cash',
    context: 'Tour step title for the cause panel that breaks down the tightest pay period.',
  },
  'tour.cause_desc': {
    text: 'This breaks down your tightest pay period. See which expenses hit hardest so you know where to cut if things get tight.',
    context: 'Tour step description for the expense cause analysis panel.',
  },
  'tour.currency_title': {
    text: 'Switch Currencies',
    context: 'Tour step title for the currency toggle button in the navigation.',
  },
  'tour.currency_desc': {
    text: 'Toggle between currencies with live exchange rates. Every number in the app converts instantly.',
    context: 'Tour step description for the currency toggle feature.',
  },
  'tour.snapshot_title': {
    text: 'Your Monthly Snapshot',
    context: 'Tour step title for the commitments summary cards.',
  },
  'tour.snapshot_desc': {
    text: 'Income vs. expenses at a glance. This is the heartbeat of your finances -- one look tells you if you are gaining or losing ground each month.',
    context: 'Tour step description for the monthly income/expense summary.',
  },
  'tour.add_title': {
    text: 'Add Anything',
    context: 'Tour step title for the add commitment button.',
  },
  'tour.add_desc': {
    text: 'Rent, subscriptions, paychecks, one-time purchases -- add them all here. The more Athena knows, the more accurate your projections get.',
    context: 'Tour step description encouraging users to add all their financial commitments.',
  },
  'tour.organized_title': {
    text: 'Organized by Category',
    context: 'Tour step title for the grouped commitment list.',
  },
  'tour.organized_desc': {
    text: 'Your commitments are grouped automatically. Click any amount to edit it. Spot a subscription you forgot about? This is where it lives.',
    context: 'Tour step description for the auto-grouped commitment categories.',
  },
  'tour.whatif_title': {
    text: 'What-If Playground',
    context: 'Tour step title for the simulation commitment toggle grid.',
  },
  'tour.whatif_desc': {
    text: 'This is where Athena gets powerful. Toggle any bill on or off, adjust amounts, and instantly see how it changes your financial future.',
    context: 'Tour step description for the interactive scenario builder.',
  },
  'tour.impact_title': {
    text: 'Instant Impact',
    context: 'Tour step title for the scenario summary panel.',
  },
  'tour.impact_desc': {
    text: 'Every change you make updates this panel in real time. See your simulated net per month and hit Run to visualize the full trajectory.',
    context: 'Tour step description for the real-time scenario summary.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Common / Shared
  // ══════════════════════════════════════════════════════════════════════
  'common.once': {
    text: 'once',
    context: 'Fallback label for one-time items when no specific date is available.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Onboarding Overlay
  // ══════════════════════════════════════════════════════════════════════
  'onboarding.title': {
    text: 'Welcome',
    context: 'Title of the onboarding overlay shown to first-time users.',
  },
  'onboarding.desc': {
    text: 'Athena projects your cash flow using your real recurring bills, income, and spending. See exactly when money gets tight before it happens.',
    context: 'Description on the onboarding overlay explaining what Athena does.',
  },
  'onboarding.demo_label': {
    text: 'Try the Demo',
    context: 'Button label for starting demo mode with sample data.',
  },
  'onboarding.demo_hint': {
    text: 'Explore with pre-loaded sample bills and income.',
    context: 'Secondary text explaining what the demo button does.',
  },
  'onboarding.setup_label': {
    text: 'Set Up My Account',
    context: 'Button label for proceeding to real account setup.',
  },
  'onboarding.setup_hint': {
    text: 'Choose your currency and start adding your own data.',
    context: 'Secondary text explaining what the setup button does.',
  },

  // ══════════════════════════════════════════════════════════════════════
  // Account Settings
  // ══════════════════════════════════════════════════════════════════════
  'settings.title': {
    text: 'Account Settings',
    context: 'Title of the settings panel that slides out from the top navigation bar.',
  },
  'settings.language': {
    text: 'Language',
    context: 'Label for the language selector dropdown in account settings.',
  },
  'settings.language_desc': {
    text: 'Choose the display language for the application.',
    context: 'Help text below the language selector explaining what it controls.',
  },
  'settings.account_currency': {
    text: 'Account Currency',
    context: 'Label for the account currency selector in settings.',
  },
  'settings.account_currency_desc': {
    text: 'The currency in which all your data is stored.',
    context: 'Help text below the account currency selector.',
  },
  'settings.change_currency': {
    text: 'Change Currency',
    context: 'Button label to initiate changing the account currency.',
  },
  'settings.currency_warning_title': {
    text: 'Change Account Currency',
    context: 'Title of the confirmation dialog when changing account currency.',
  },
  'settings.currency_warning': {
    text: 'Changing your account currency will convert all commitment amounts and balance data to the new currency using the latest exchange rate. This may not accurately reflect historic values. This action cannot be undone.',
    context: 'Warning message shown in the confirmation dialog before changing account currency. Must clearly communicate the irreversibility and potential inaccuracy.',
  },
  'settings.currency_confirm': {
    text: 'Convert to {currency}',
    context: 'Confirmation button in the currency change dialog. {currency} is the target currency code like "KRW".',
  },
  'settings.currency_cancel': {
    text: 'Cancel',
    context: 'Cancel button in the currency change confirmation dialog.',
  },
  'settings.currency_converting': {
    text: 'Converting...',
    context: 'Button label shown while the currency conversion is in progress.',
  },
  'settings.saved': {
    text: 'Saved',
    context: 'Brief confirmation shown after a setting is successfully saved.',
  },
}

export default en_US
