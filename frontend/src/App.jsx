import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRight, Check, ChevronDown, CircleHelp, ExternalLink, Globe2, LayoutGrid, ListFilter, Plus, RefreshCw, Search, Settings2, ShieldCheck, Trash2, WandSparkles, X } from 'lucide-react'
import { api } from './api'

const emptyOptions = { domains: [], groups: [], sources: [], offers: [] }
const catalogLabels = { domains: 'домены', groups: 'группы', sources: 'источники трафика', offers: 'офферы' }
const isAvailable = item => item.state === undefined || item.state === 'active'

function nameOf(items, id) {
  return items.find(item => item.id === id)?.name || `#${id}`
}

function offerWord(count) {
  const tail = count % 100
  if (tail >= 11 && tail <= 14) return 'офферов'
  if (count % 10 === 1) return 'оффер'
  if (count % 10 >= 2 && count % 10 <= 4) return 'оффера'
  return 'офферов'
}

function SearchSelect({ label, items, value, onChange, placeholder = 'Выберите...', disabled = false }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const selected = items.find(item => item.id === Number(value))
  const filtered = items.filter(item => item.state !== 'deleted' && `${item.name} ${item.id}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="field select-field">
    <label>{label}</label>
    <button className={`select-trigger ${open ? 'focus' : ''}`} type="button" disabled={disabled || !items.length} onClick={() => { setOpen(!open); setQuery('') }}>
      <span className={selected ? '' : 'muted'}>{selected ? selected.name : placeholder}</span><ChevronDown size={17} />
    </button>
    {open && items.length > 0 && <div className="select-menu">
      <div className="select-search"><Search size={15} /><input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder="Поиск по названию или ID" /></div>
      <div className="select-options">{filtered.length ? filtered.map(item => <button type="button" key={item.id} className={item.id === Number(value) ? 'chosen' : ''} onClick={() => { onChange(item.id); setOpen(false) }}><span>{item.name}</span><small>#{item.id}</small></button>) : <p className="empty-search">Ничего не найдено</p>}</div>
    </div>}
  </div>
}

function Stat({ icon: Icon, label, value, tone }) {
  return <div className="stat"><span className={`stat-icon ${tone}`}><Icon size={19} /></span><div><span className="stat-label">{label}</span><strong>{value}</strong></div></div>
}

function CreateView({ options, mode, onCreated, notify }) {
  const [form, setForm] = useState({ name: '', geo: '', offer_id: '', domain_id: '', group_id: '', traffic_source_id: '' })
  const [saving, setSaving] = useState(false)
  const geo = [...new Set(form.geo.split(/[\s,;]+/).map(value => value.trim().toUpperCase()).filter(Boolean))]
  const validGeo = geo.length > 0 && geo.every(value => /^[A-Z]{2}$/.test(value))
  const catalogs = Object.fromEntries(Object.entries(options).map(([key, rows]) => [key, rows.filter(isAvailable)]))
  const missing = Object.entries(catalogLabels).filter(([key]) => !catalogs[key].length).map(([, label]) => label)
  const ready = form.name.trim() && validGeo && [
    ['offers', 'offer_id'], ['domains', 'domain_id'], ['groups', 'group_id'], ['sources', 'traffic_source_id'],
  ].every(([key, field]) => catalogs[key].some(item => item.id === form[field]))
  const update = (key, value) => setForm(previous => ({ ...previous, [key]: value }))
  async function submit(event) {
    event.preventDefault()
    if (!ready) return
    setSaving(true)
    try {
      const result = await api('/campaigns', { method: 'POST', body: JSON.stringify({ name: form.name.trim(), geo, offer_id: Number(form.offer_id), domain_id: Number(form.domain_id), group_id: Number(form.group_id), traffic_source_id: Number(form.traffic_source_id) }) })
      notify('Кампания создана с двумя потоками', 'success')
      setForm({ name: '', geo: '', offer_id: '', domain_id: '', group_id: '', traffic_source_id: '' })
      onCreated(result)
    } catch (error) { notify(error.message, 'error') }
    finally { setSaving(false) }
  }
  return <div className="content-grid">
    <section className="panel form-panel">
      <div className="panel-heading"><div className="panel-icon violet"><WandSparkles size={20} /></div><div><h2>Новая кампания</h2><p>Заполните параметры для Keitaro</p></div></div>
      {missing.length > 0 && <p className="toast error" role="status">Создание кампании недоступно. {mode === 'live' ? 'Keitaro не вернул доступные справочники' : 'Не загружены справочники'}: {missing.join(', ')}.</p>}
      <form onSubmit={submit}>
        <div className="field"><label htmlFor="campaign-name">Название кампании <span className="required">*</span></label><input id="campaign-name" value={form.name} onChange={event => update('name', event.target.value)} placeholder="Например, Summer launch / MX" maxLength={255} /></div>
        <div className="field"><label htmlFor="geo">ГЕО <span className="required">*</span></label><div className="input-with-icon"><Globe2 size={18} /><input id="geo" value={form.geo} onChange={event => update('geo', event.target.value)} placeholder="MX, AU, RO" /></div><small className={form.geo && !validGeo ? 'hint-error' : 'hint'}>Двухбуквенные коды стран через запятую</small></div>
        <SearchSelect label="Оффер Keitaro *" items={catalogs.offers} value={form.offer_id} onChange={value => update('offer_id', value)} placeholder={catalogs.offers.length ? 'Найти оффер' : 'Нет доступных офферов'} />
        <div className="form-divider"><span>Настройки кампании</span></div>
        <div className="form-row"><SearchSelect label="Домен *" items={catalogs.domains} value={form.domain_id} onChange={value => update('domain_id', value)} placeholder={catalogs.domains.length ? 'Выберите...' : 'Нет доступных доменов'} /><SearchSelect label="Группа *" items={catalogs.groups} value={form.group_id} onChange={value => update('group_id', value)} placeholder={catalogs.groups.length ? 'Выберите...' : 'Нет доступных групп'} /></div>
        <SearchSelect label="Источник трафика *" items={catalogs.sources} value={form.traffic_source_id} onChange={value => update('traffic_source_id', value)} placeholder={catalogs.sources.length ? 'Выберите...' : 'Нет доступных источников'} />
        <button className="primary-button create-button" type="submit" disabled={!ready || saving}>{saving ? 'Создаём...' : 'Создать кампанию'} <ArrowRight size={18} /></button>
      </form>
    </section>
    <aside className="side-stack">
      <section className="panel preview-panel"><div className="side-heading"><div className="panel-icon blue"><ListFilter size={19} /></div><h3>Как будет работать</h3></div><div className="flow-preview"><div className="flow-number">01</div><div><strong>ГЕО → Google</strong><p>Трафик из {validGeo ? geo.join(', ') : 'указанных стран'} уйдёт на Google.</p><span className="flow-tag">Фильтр по стране</span></div></div><div className="flow-connector" /><div className="flow-preview"><div className="flow-number second">02</div><div><strong>Остальной трафик → оффер</strong><p>{form.offer_id ? nameOf(options.offers, Number(form.offer_id)) : 'Выбранный оффер Keitaro'} получит оставшиеся переходы.</p><span className="flow-tag green">Поток по умолчанию</span></div></div></section>
      <section className="tip-card"><ShieldCheck size={19} /><div><strong>Настройки из Keitaro</strong><p>Домены, группы, источники и офферы загружаются через API. После создания можно изменять доли офферов в редакторе.</p></div></section>
    </aside>
  </div>
}

function EditorView({ campaigns, options, selectedId, selectCampaign, detail, setDetail, notify, refresh }) {
  const [query, setQuery] = useState('')
  const [newOfferId, setNewOfferId] = useState('')
  const [draft, setDraft] = useState([])
  const [busy, setBusy] = useState(false)
  const stream = detail?.streams?.find(item => item.offers?.length || item.schema === 'landings')
  useEffect(() => { setDraft(stream?.offers?.map(item => ({ offer_id: item.offer_id, share: item.share })) || []); setNewOfferId('') }, [detail?.id, stream?.id, JSON.stringify(stream?.offers)])
  const total = draft.reduce((sum, item) => sum + (Number(item.share) || 0), 0)
  const original = stream?.offers?.map(item => ({ offer_id: item.offer_id, share: item.share })) || []
  const dirty = JSON.stringify(draft) !== JSON.stringify(original)
  const available = options.offers.filter(item => isAvailable(item) && !draft.some(existing => existing.offer_id === item.id) && `${item.name} ${item.id}`.toLowerCase().includes(query.toLowerCase()))
  async function mutate(path, method, body, success) {
    setBusy(true)
    try { const updated = await api(path, { method, ...(body ? { body: JSON.stringify(body) } : {}) }); setDetail(updated); setDraft(updated.streams.find(item => item.id === stream.id).offers.map(item => ({ offer_id: item.offer_id, share: item.share }))); notify(success, 'success'); refresh() }
    catch (error) { notify(error.message, 'error') }
    finally { setBusy(false) }
  }
  const base = stream ? `/campaigns/${detail.id}/streams/${stream.id}/offers` : ''
  return <div className="content-grid editor-grid">
    <section className="panel editor-panel">
      <div className="panel-heading"><div className="panel-icon violet"><Settings2 size={20} /></div><div><h2>Редактор кампании</h2><p>Добавляйте офферы и настраивайте распределение</p></div></div>
      <div className="field"><label htmlFor="campaign-choice">Кампания</label><div className="native-select"><select id="campaign-choice" value={selectedId || ''} onChange={event => selectCampaign(Number(event.target.value))}><option value="" disabled>Выберите кампанию</option>{campaigns.map(item => <option key={item.id} value={item.id}>{item.name} (#{item.id})</option>)}</select><ChevronDown size={17} /></div></div>
      {detail && <><div className="campaign-summary"><div><span className="eyebrow">КАМПАНИЯ #{detail.id}</span><h3>{detail.name}</h3><div className="summary-chips"><span><Globe2 size={14} /> {detail.geo?.length ? detail.geo.join(', ') : '—'}</span><span>{nameOf(options.groups, detail.group_id)}</span><span>{nameOf(options.sources, detail.traffic_source_id)}</span></div></div><span className="status"><i /> Активна</span></div>
        <div className="section-title"><div><h3>Офферы в потоке</h3><p>{stream ? `Поток «${stream.name}» · ID ${stream.id}` : 'Поток с офферами не найден'}</p></div><span className="count-pill">{draft.length} {offerWord(draft.length)}</span></div>
        {stream && <><div className="offer-list">{draft.map(item => <div className="offer-row" key={item.offer_id}><div className="offer-avatar">{nameOf(options.offers, item.offer_id).slice(0, 1).toUpperCase()}</div><div className="offer-identity"><strong>{nameOf(options.offers, item.offer_id)}</strong><span>ID {item.offer_id}</span></div><div className="share-control"><input aria-label={`Доля оффера ${item.offer_id}`} type="number" min="0" max="100" value={item.share} onChange={event => setDraft(previous => previous.map(row => row.offer_id === item.offer_id ? { ...row, share: event.target.value === '' ? '' : Number(event.target.value) } : row))} /><span>%</span></div><button className="icon-button danger" title="Удалить оффер" aria-label={`Удалить оффер ${item.offer_id}`} disabled={busy || draft.length <= 1} onClick={() => mutate(`${base}/${item.offer_id}`, 'DELETE', null, 'Оффер удалён; доли распределены поровну')}><Trash2 size={17} /></button></div>)}</div>
          <div className="share-footer"><span>Сумма долей</span><strong className={total === 100 ? 'total-ok' : 'total-error'}>{total}% / 100%</strong></div>
          <div className="editor-actions"><button className="secondary-button" disabled={busy || !draft.length} onClick={() => setDraft(draft.map((item, index) => ({ ...item, share: Math.floor(100 / draft.length) + (index < 100 % draft.length ? 1 : 0) })))}>Распределить поровну</button><button className="primary-button" disabled={busy || !dirty || total !== 100 || draft.some(item => item.share === '' || item.share < 0 || item.share > 100)} onClick={() => mutate(base, 'PUT', { offers: draft }, 'Доли офферов сохранены')}>Сохранить доли <Check size={17} /></button></div>
          <div className="add-offer"><div className="section-title"><div><h3>Добавить оффер</h3><p>Выберите оффер из Keitaro</p></div></div><div className="add-row"><div className="offer-picker"><Search size={17} /><input aria-label="Поиск оффера" value={query} onChange={event => { setQuery(event.target.value); setNewOfferId('') }} placeholder="Поиск по названию или ID" /><select aria-label="Выберите оффер" value={newOfferId} onChange={event => setNewOfferId(event.target.value)}><option value="">Выберите оффер</option>{available.map(item => <option key={item.id} value={item.id}>{item.name} (#{item.id})</option>)}</select></div><button className="primary-button add-button" disabled={busy || !newOfferId} onClick={() => mutate(base, 'POST', { offer_id: Number(newOfferId) }, 'Оффер добавлен; доли распределены поровну')}><Plus size={18} /> Добавить</button></div></div></>}
      </>}
      {!detail && <div className="empty-state"><LayoutGrid size={30} /><h3>Кампаний пока нет</h3><p>Создайте первую кампанию, чтобы редактировать её потоки.</p></div>}
    </section>
    <aside className="side-stack"><section className="panel preview-panel"><div className="side-heading"><div className="panel-icon blue"><Activity size={19} /></div><h3>Обзор потоков</h3></div>{detail?.streams?.length ? detail.streams.map((item, index) => <div className="mini-flow" key={item.id}><span className="mini-index">0{index + 1}</span><div><strong>{item.name}</strong><p>{item.type === 'default' ? 'Поток по умолчанию' : 'Фильтр по ГЕО'} · {item.offers?.length || 0} {offerWord(item.offers?.length || 0)}</p></div><span className="mini-dot" /></div>) : <p className="aside-empty">Выберите кампанию, чтобы увидеть потоки.</p>}</section><section className="tip-card"><CircleHelp size={19} /><div><strong>Точные доли</strong><p>При добавлении или удалении оффера доли пересчитываются поровну. Ручное изменение можно сохранить, когда сумма равна 100%.</p></div></section></aside>
  </div>
}

export default function App() {
  const [view, setView] = useState('create')
  const [mode, setMode] = useState('demo')
  const [options, setOptions] = useState(emptyOptions)
  const [campaigns, setCampaigns] = useState([])
  const [activity, setActivity] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState(null)
  const notify = (message, type) => { setNotice({ message, type }); window.setTimeout(() => setNotice(null), 5000) }
  async function refresh() {
    try { const [health, newOptions, newCampaigns, newActivity] = await Promise.all([api('/health'), api('/options'), api('/campaigns'), api('/activity')]); setMode(health.mode); setOptions(newOptions); setCampaigns(newCampaigns); setActivity(newActivity); if (!selectedId && newCampaigns.length) setSelectedId(newCampaigns[0].id) }
    catch (error) { notify(error.message, 'error') }
    finally { setLoading(false) }
  }
  useEffect(() => { refresh() }, [])
  useEffect(() => { if (selectedId) api(`/campaigns/${selectedId}`).then(setDetail).catch(error => notify(error.message, 'error')); else setDetail(null) }, [selectedId])
  async function onCreated(result) { setSelectedId(result.id); setDetail(result); setView('editor'); await refresh() }
  const campaignCount = campaigns.length
  const offerCount = options.offers.length
  const recent = useMemo(() => activity.slice(0, 4), [activity])
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><span /></div><div><strong>adrobot<span className="brand-dot">.</span></strong><small>KEITARO WORKSPACE</small></div></div><div className="workspace-title">РАБОЧЕЕ ПРОСТРАНСТВО</div><nav><button className={view === 'create' ? 'nav-item active' : 'nav-item'} onClick={() => setView('create')}><Plus size={19} /> Создать кампанию</button><button className={view === 'editor' ? 'nav-item active' : 'nav-item'} onClick={() => setView('editor')}><Settings2 size={19} /> Редактор кампаний <span className="nav-count">{campaignCount}</span></button></nav><div className="sidebar-bottom"><div className="sidebar-help"><CircleHelp size={18} /><div><strong>Нужна помощь?</strong><p>Документация API Keitaro</p></div><a href="https://admin-api.docs.keitaro.io/" target="_blank" rel="noreferrer" aria-label="Открыть документацию"><ExternalLink size={15} /></a></div><div className="sidebar-mode"><span className="mode-indicator" /><div><strong>{mode === 'demo' ? 'Демо режим' : 'Keitaro подключен'}</strong><small>{mode === 'demo' ? 'Локальные данные SQLite' : 'Admin API · live'}</small></div></div></div></aside>
    <main className="main"><header className="topbar"><div className="breadcrumbs">Workspace <span>/</span> <strong>{view === 'create' ? 'Создать кампанию' : 'Редактор кампаний'}</strong></div><button className="refresh-button" onClick={refresh} title="Обновить данные"><RefreshCw size={17} /> <span>Обновить</span></button></header><div className="main-content"><div className="page-intro"><div><div className="eyebrow page-eyebrow"><span /> CAMPAIGN MANAGEMENT</div><h1>{view === 'create' ? 'Создать кампанию' : 'Редактор кампаний'}</h1><p>{view === 'create' ? 'Создайте кампанию с ГЕО фильтром и оффером за пару шагов.' : 'Управляйте офферами и долями трафика в существующих кампаниях.'}</p></div><div className="intro-badge"><Globe2 size={17} /> Keitaro Admin API</div></div>
      <div className="stats-row"><Stat icon={LayoutGrid} label="Кампании" value={campaignCount} tone="purple" /><Stat icon={ListFilter} label="Офферы" value={offerCount} tone="cyan" /><Stat icon={ShieldCheck} label="Подключение" value={mode === 'demo' ? 'Демо' : 'Live'} tone="green" /></div>
      {notice && <div className={`toast ${notice.type}`} role="alert"><span>{notice.message}</span><button onClick={() => setNotice(null)} aria-label="Закрыть"><X size={16} /></button></div>}
      {loading ? <div className="loading">Загружаем данные...</div> : view === 'create' ? <CreateView options={options} mode={mode} onCreated={onCreated} notify={notify} /> : <EditorView campaigns={campaigns} options={options} selectedId={selectedId} selectCampaign={setSelectedId} detail={detail} setDetail={setDetail} notify={notify} refresh={refresh} />}
      <section className="activity-section"><div className="activity-title"><div><h2>Последние действия</h2><p>История операций в рабочем пространстве</p></div></div><div className="activity-list">{recent.length ? recent.map(item => <div className="activity-item" key={item.id}><span className="activity-symbol"><Activity size={16} /></span><span>{item.summary}</span><small>{new Date(item.created_at + 'Z').toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</small></div>) : <div className="activity-empty">Здесь появятся созданные кампании и изменения офферов.</div>}</div></section>
    </div></main>
  </div>
}
