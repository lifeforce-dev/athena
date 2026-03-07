/**
 * Korean (South Korea) locale.
 *
 * Register: 합쇼체 (formal polite) for UI and instructional text.
 *           해요체 for conversational tour descriptions.
 * Plurals:  Korean has no grammatical plural — ICU plural blocks use only `other`.
 */

const ko_KR: Record<string, string> = {
  // ══════════════════════════════════════════════════════════════════════
  // Navigation
  // ══════════════════════════════════════════════════════════════════════
  'nav.dashboard': '대시보드',
  'nav.commitments': '약정',
  'nav.simulation': '시뮬레이션',
  'nav.logout': '로그아웃',

  // ══════════════════════════════════════════════════════════════════════
  // Login page
  // ══════════════════════════════════════════════════════════════════════
  'login.brand': 'Athena',
  'login.version': 'v1',
  'login.tagline': '현금 흐름 예측 및 재정 관리 서비스',
  'login.sign_in': 'Discord로 로그인',
  'login.demo': '데모 체험',
  'login.demo_sub': '계정이 필요 없습니다',
  'login.secure': 'OAuth 2.0을 통한 안전한 세션',

  // ══════════════════════════════════════════════════════════════════════
  // Dashboard
  // ══════════════════════════════════════════════════════════════════════
  'dash.bills_this_week': '이번 주 청구서',
  'dash.resets': '{date}에 초기화',
  'dash.loading': '예측 데이터 로딩 중...',
  'dash.no_data_title': '예측 데이터 없음',
  'dash.no_data_desc': '약정을 추가하여 현금 흐름 추이를 확인하십시오.',

  // Dashboard Hero
  'hero.current_balance': '현재 잔액',
  'hero.save': '저장',
  'hero.esc': 'Esc',
  'hero.critical': '위험',
  'hero.tight': '빠듯함',
  'hero.comfortable': '여유',
  'hero.days_projected': '{count}일 예측',
  'hero.after_window': '기간 후',
  'hero.lowest_point': '최저점',
  'hero.net_change': '순 변동',

  // ══════════════════════════════════════════════════════════════════════
  // Bills This Week panel
  // ══════════════════════════════════════════════════════════════════════
  'bills.empty': '이번 주 남은 청구서가 없습니다',
  'bills.total': '합계',
  'bills.next_week': '다음 주 — 청구서 {amount}',

  // ══════════════════════════════════════════════════════════════════════
  // Cause Panel (tightest pay period)
  // ══════════════════════════════════════════════════════════════════════
  'cause.title': '가장 빠듯한 급여 기간',
  'cause.total': '합계 {amount}',
  'cause.window_range': '가장 빠듯한 기간: {range}',

  // ══════════════════════════════════════════════════════════════════════
  // Shortfall Warning
  // ══════════════════════════════════════════════════════════════════════
  'shortfall.goes_negative': '{date}에 잔액이 마이너스가 됩니다',
  'shortfall.projected': '예상 부족액 {amount}',
  'shortfall.recovery': ' — 다음 급여 {date}',
  'shortfall.at_risk': '{count, plural, other {#건의 약정이 위험합니다}}',
  'shortfall.total': '-{amount} 합계',

  // ══════════════════════════════════════════════════════════════════════
  // Trajectory Chart
  // ══════════════════════════════════════════════════════════════════════
  'chart.title': '잔액 추이',
  'chart.hover_hint': '차트 위에 마우스를 올려 확인하십시오',
  'chart.range_days': '{count}일',
  'chart.today': '오늘',
  'chart.day_offset': '+{count}일',

  // ══════════════════════════════════════════════════════════════════════
  // Event List
  // ══════════════════════════════════════════════════════════════════════
  'events.title': '예정된 일정',
  'events.count': '{count}건',
  'events.col_day': '날짜',
  'events.col_name': '이름',
  'events.col_amount': '금액',
  'events.col_balance': '잔액',

  // ══════════════════════════════════════════════════════════════════════
  // Paycheck Bands
  // ══════════════════════════════════════════════════════════════════════
  'bands.spent': '지출 {amount}',
  'bands.min': '최소 {amount}',
  'bands.partial': '(진행 중)',
  'bands.start': '시작',
  'bands.end': '종료',
  'bands.net': '순수익',

  // ══════════════════════════════════════════════════════════════════════
  // Commitments page
  // ══════════════════════════════════════════════════════════════════════
  'commit.page_title': '약정',
  'commit.page_desc': '현금 흐름 추이를 구성하는 정기 지출, 수입 및 일회성 결제를 관리하십시오.',
  'commit.monthly_income': '월간 수입',
  'commit.monthly_expenses': '월간 지출',
  'commit.net_per_month': '월 순수익',
  'commit.total_items': '전체 항목',
  'commit.add': '약정 추가',
  'commit.loading': '약정 로딩 중...',
  'commit.col_name': '이름',
  'commit.col_amount': '금액',
  'commit.col_freq': '빈도',
  'commit.col_next': '다음',
  'commit.per_month': '/월',
  'commit.one_time_title': '일회성 결제 ({count})',
  'commit.total': '합계 {amount}',
  'commit.col_date': '날짜',
  'commit.remove': '삭제',
  'commit.group_income': '수입',
  'commit.group_expenses': '지출',

  // Frequency labels
  'freq.monthly': '월간',
  'freq.biweekly': '격주',
  'freq.weekly': '주간',
  'freq.daily': '일간',
  'freq.custom': '사용자 지정',
  'freq.once': '일회성',

  // ══════════════════════════════════════════════════════════════════════
  // Commitment Modal
  // ══════════════════════════════════════════════════════════════════════
  'modal.add_title': '약정 추가',
  'modal.edit_title': '약정 수정',
  'modal.name': '이름',
  'modal.name_placeholder': '예: Netflix, 자동차 할부금',
  'modal.amount': '금액 ({symbol})',
  'modal.type': '유형',
  'modal.type_expense': '지출',
  'modal.type_income': '수입',
  'modal.frequency': '빈도',
  'modal.day_of_month': '매월 결제일',
  'modal.date': '날짜',
  'modal.starting_from': '시작 기준일',
  'modal.start_date': '시작 날짜',
  'modal.cancel': '취소',
  'modal.saving': '저장 중...',
  'modal.save': '저장',

  // ══════════════════════════════════════════════════════════════════════
  // Simulation page
  // ══════════════════════════════════════════════════════════════════════
  'sim.running': '시뮬레이션 실행 중...',
  'sim.current': '현재',
  'sim.after_window': '기간 후',
  'sim.lowest_point': '최저점',
  'sim.avg_gained': '월평균 수익',
  'sim.monthly_breakdown': '월별 상세',
  'sim.months_count': '{count}개월',
  'sim.no_data_title': '데이터 없음',
  'sim.no_data_desc': '선택한 기간에 대한 예측 데이터가 없습니다. 약정과 잔액을 확인하십시오.',
  'sim.summary_title': '시나리오 요약',
  'sim.start_date': '시작일',
  'sim.end_date': '종료일',
  'sim.net_per_month': '시뮬레이션 월 순수익',
  'sim.income': '수입',
  'sim.expenses': '지출',
  'sim.active_items': '활성 항목',
  'sim.savings_from_cuts': '삭감 절약액',
  'sim.disabled_count': '{count}건 비활성화',
  'sim.edited_count': '{count}건 수정',
  'sim.reset': '초기화',
  'sim.run_button': '시뮬레이션 실행',
  'sim.running_button': '실행 중...',
  'sim.day_window': '{count}일 기간',
  'sim.configure_title': '설정 및 실행',
  'sim.configure_desc': '약정을 켜고 끄거나 금액을 조정한 후 "시뮬레이션 실행"을 클릭하여 현금 흐름을 예측하십시오.',

  // Scenario Commitments panel
  'scenario.income': '수입 ({count})',
  'scenario.expenses': '지출 ({count})',
  'scenario.one_time': '일회성 ({count})',

  // ══════════════════════════════════════════════════════════════════════
  // Currency Prompt (initial setup)
  // ══════════════════════════════════════════════════════════════════════
  'currency_prompt.title': '통화 설정',
  'currency_prompt.desc': '계정 통화를 선택하십시오. 모든 금액이 이 통화로 저장 및 표시됩니다.',
  'currency_prompt.continue': '계속',
  'currency_prompt.saving': '저장 중...',
  'currency_prompt.lang_info': '기본 언어가 다음으로 설정됩니다',

  // ══════════════════════════════════════════════════════════════════════
  // Currency Explainer (one-time popup)
  // ══════════════════════════════════════════════════════════════════════
  'explainer.title': '표시 통화',
  'explainer.body': '계정의 모든 금액은 {accountCurrency}로 저장됩니다. {displayCurrency}로 전환하면 현재 환율로 변환됩니다. 소폭의 반올림 차이는 정상입니다.',
  'explainer.you_enter': '입력 금액',
  'explainer.stored_as': '저장 형태',
  'explainer.saved': '저장됨',
  'explainer.displayed_as': '표시 형태',
  'explainer.you_see': '표시 금액',
  'explainer.difference': '{delta} 차이',
  'explainer.dismiss': '확인',

  // ══════════════════════════════════════════════════════════════════════
  // First-Time Experience (FTE)
  // ══════════════════════════════════════════════════════════════════════
  'fte.welcome_title': 'Athena에 오신 것을 환영합니다',
  'fte.welcome_desc': '샘플 데이터를 사용하여 각 섹션을 안내해 드리겠습니다.',
  'fte.welcome_hint': '위의 빛나는 대시보드 탭을 클릭하여 시작하십시오.',
  'fte.skip_tour': '둘러보기 건너뛰기',
  'fte.complete_title': '모든 준비가 완료되었습니다!',
  'fte.complete_desc': '이제 실제 데이터를 설정하고 재정을 관리하십시오.',
  'fte.complete_button': '대시보드로 이동',

  // ══════════════════════════════════════════════════════════════════════
  // Guided Tours
  // ══════════════════════════════════════════════════════════════════════
  'tour.balance_title': '잔액 한눈에 보기',
  'tour.balance_desc': '실제 은행 잔액이에요. 언제든 탭하면 업데이트할 수 있고, 모든 수치가 즉시 재계산돼요.',
  'tour.gauge_title': '재정 건강 방패',
  'tour.gauge_desc': '초록색은 순항, 노란색은 빠듯함, 빨간색은 조치가 필요해요. 90일 앞을 미리 보여주기 때문에 갑작스러운 상황이 없어요.',
  'tour.bills_title': '다가오는 청구서',
  'tour.bills_desc': '이번 주와 다음 주에 결제되는 항목을 정확히 볼 수 있어요. 어떤 청구서가 언제 나가는지 더 이상 헷갈릴 일이 없어요.',
  'tour.trajectory_title': '현금 흐름 추이',
  'tour.trajectory_desc': '앞으로 90일간의 자금 흐름을 일별로 보여줘요. 아무 지점이나 가리키면 정확한 내역을 확인할 수 있어요. 하락 구간에 주의하세요.',
  'tour.cause_title': '지출의 원인',
  'tour.cause_desc': '가장 빠듯한 급여 기간을 분석해줘요. 어떤 지출이 가장 부담되는지 파악해서 필요할 때 어디를 줄일지 알 수 있어요.',
  'tour.currency_title': '통화 전환',
  'tour.currency_desc': '실시간 환율로 통화를 전환할 수 있어요. 앱의 모든 수치가 즉시 변환돼요.',
  'tour.snapshot_title': '월간 요약',
  'tour.snapshot_desc': '수입 대 지출을 한눈에 볼 수 있어요. 매월 자산이 늘고 있는지 줄고 있는지 한 번에 파악할 수 있어요.',
  'tour.add_title': '무엇이든 추가',
  'tour.add_desc': '월세, 구독, 급여, 일회성 구매 등 모두 여기에 추가하세요. Athena가 더 많이 알수록 예측이 더 정확해져요.',
  'tour.organized_title': '카테고리별 정리',
  'tour.organized_desc': '약정이 자동으로 분류돼요. 금액을 클릭하면 수정할 수 있어요. 잊고 있던 구독이 있나요? 여기서 확인하세요.',
  'tour.whatif_title': '가정 시나리오',
  'tour.whatif_desc': 'Athena의 핵심 기능이에요. 청구서를 켜고 끄거나 금액을 조정하면 재정 미래가 어떻게 바뀌는지 즉시 확인할 수 있어요.',
  'tour.impact_title': '즉각적인 반영',
  'tour.impact_desc': '변경할 때마다 이 패널이 실시간으로 업데이트돼요. 시뮬레이션 월 순수익을 확인하고 실행을 눌러 전체 추이를 시각화하세요.',

  // ══════════════════════════════════════════════════════════════════════
  // Common / Shared
  // ══════════════════════════════════════════════════════════════════════
  'common.once': '일회',

  // ══════════════════════════════════════════════════════════════════════
  // Onboarding Overlay
  // ══════════════════════════════════════════════════════════════════════
  'onboarding.title': '환영합니다',
  'onboarding.desc': 'Athena는 실제 정기 청구서, 수입, 지출을 기반으로 현금 흐름을 예측합니다. 자금이 부족해지기 전에 미리 확인하십시오.',
  'onboarding.demo_label': '데모 체험',
  'onboarding.demo_hint': '미리 준비된 샘플 청구서와 수입으로 탐색해 보십시오.',
  'onboarding.setup_label': '계정 설정',
  'onboarding.setup_hint': '통화를 선택하고 직접 데이터를 추가하십시오.',

  // ══════════════════════════════════════════════════════════════════════
  // Account Settings
  // ══════════════════════════════════════════════════════════════════════
  'settings.title': '계정 설정',
  'settings.language': '언어',
  'settings.language_desc': '앱의 표시 언어를 선택하십시오.',
  'settings.account_currency': '계정 통화',
  'settings.account_currency_desc': '모든 데이터가 저장되는 통화입니다.',
  'settings.change_currency': '통화 변경',
  'settings.currency_warning_title': '계정 통화 변경',
  'settings.currency_warning': '계정 통화를 변경하면 모든 약정 금액과 잔액 데이터가 최신 환율을 사용하여 새 통화로 변환됩니다. 과거 수치를 정확하게 반영하지 못할 수 있습니다. 이 작업은 되돌릴 수 없습니다.',
  'settings.currency_confirm': '{currency}(으)로 변환',
  'settings.currency_cancel': '취소',
  'settings.currency_converting': '변환 중...',
  'settings.saved': '저장됨',
  'settings.language_refresh': '새 언어를 완전히 적용하려면 페이지를 새로고침하십시오.',
  'settings.replay_tour': '가이드 둘러보기',
  'settings.replay_tour_desc': '앱의 각 섹션을 소개하는 가이드 둘러보기를 다시 확인하십시오.',
  'settings.replay_tour_btn': '둘러보기 다시 보기',
  'settings.replay_tour_refresh': '둘러보기를 시작하려면 페이지를 새로고침하십시오.',
}

export default ko_KR
