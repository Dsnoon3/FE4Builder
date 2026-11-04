"""Grouped editor navigation with a cross-category search."""
import tkinter as tk
from tkinter import ttk


def build_home(app):
    home=ttk.Frame(app,padding=24)
    ttk.Label(home,text='FE4Builder editors',style='Title.TLabel').pack(anchor='w')
    header=ttk.Frame(home);header.pack(fill='x',pady=(8,16))
    ttk.Label(header,text='Choose a category or search for a tool.',style='Subtitle.TLabel').pack(side='left')
    ttk.Label(header,text='Find editor').pack(side='left',padx=(28,8))
    search=tk.StringVar();ttk.Entry(header,textvariable=search,width=36).pack(side='left',fill='x',expand=True)
    tabs=ttk.Notebook(home);tabs.pack(fill='both',expand=True)
    editor=lambda mode:lambda:app.show_editor(mode)
    groups={
        'Characters':[
            ('Character Editor','Playable characters, growths, equipment and promotion targets.',editor('Character Editor')),
            ('Class Editor','Class bases, growths, weapon ranks and sprite sheets.',editor('Class Editor')),
            ('Enemy Editor','Generic enemy classes, levels, equipment and identities.',editor('Enemy Editor')),
            ('Holy Character Editor','Individual stats, skills and holy blood for special enemies.',editor('Holy Character Editor'))],
        'Items':[
            ('Item Editor','Weapons, staves, rings, icons and battle previews.',editor('Item Editor')),
            ('Shop Editor','Shop inventories and their shared item slots.',editor('Shop Editor')),
            ('Stat Bonus Editor','Shared weapon profiles and ring bonus amounts.',app.edit_stat_bonuses)],
        'Maps & Events':[
            ('Objectives & Progression','Existing seize / defeat triggers, ending events and global defeat rules.',app.edit_objectives),
            ('Event Editor','Edit chapter events, unit commands, dialogue, audio, camera routes and flags.',app.edit_events),
            ('AI Viewer','Inspect faction AI groups, behavior scripts, assigned units and shared uses.',app.view_ai),
            ('Reinforcement Editor','Change existing spawn positions, movement speeds and verified turn triggers.',app.edit_reinforcements),
            ('Recruitment & Conversations','Existing talk participants, dialogue links and recruitment commands.',app.edit_conversations),
            ('Map Editor','Paint terrain and resize chapter camera bounds.',app.edit_map),
            ('Map Army Editor','View deployments and drag units into position.',app.edit_army_map),
            ('Army Editor','Deployment records, groups, AI and equipment.',editor('Army Editor')),
            ('Village Rewards','Village item and stat rewards, plus additional visit gold.',app.edit_villages)],
        'Graphics & Text':[
            ('Portrait Editor','Preview, import and export full portrait sheets.',app.edit_portrait),
            ('Character Name Editor','Edit playable character names.',app.edit_name),
            ('Dialogue Editor','Chapter conversations, control tags and text previews.',app.edit_dialogue),
            ('Tileset Viewer / Exporter','Browse and export chapter tilesets.',app.view_tilesets),
            ('Music & Sound Player','Read-only native music, effect and word-command previews.',app.open_audio),
            ('Background Editor','Preview, export and replace the six dialogue backgrounds.',app.edit_background),
            ('Intro & Title Editor','Opening scenes, logos and title-screen graphics.',app.edit_intro)],
        'Advanced':[
            ('Character Settings','Promotion tables and other character-related modules.',editor('Character Settings')),
            ('Children Settings','Inheritance and other children-related modules.',editor('Children Settings')),
            ('Class Settings','Movement, terrain and other class-related modules.',editor('Class Settings')),
            ('Love Editor','Pairing and relationship tables.',editor('Love Editor')),
            ('Music & Other Tables','Music and miscellaneous Nightmare modules.',editor('Music & Other Tables')),
            ('Patches','Install or remove optional game-code features.',app.edit_patches)]}
    all_tools=[(category,*tool) for category,tools in groups.items() for tool in tools]
    app.home_tools=all_tools;app.home_tabs=tabs;app.home_search=search
    def cards(frame,tools):
        for widget in frame.winfo_children():widget.destroy()
        columns=3 if len(tools)>6 else 2
        for column in range(columns):frame.columnconfigure(column,weight=1)
        for i,(name,description,command) in enumerate(tools):
            card=ttk.Frame(frame,padding=12,relief='groove')
            card.grid(row=i//columns,column=i%columns,sticky='nsew',padx=8,pady=8)
            ttk.Button(card,text=name,command=command).pack(fill='x',ipady=8)
            ttk.Label(card,text=description,wraplength=240 if columns==3 else 360,style='Subtitle.TLabel').pack(anchor='w',pady=(8,0))
    for category,tools in groups.items():
        frame=ttk.Frame(tabs,padding=8);tabs.add(frame,text=category);cards(frame,tools)
    results=ttk.Frame(tabs,padding=8)
    previous=[None]
    def filter_tools(*_):
        query=search.get().strip().casefold()
        if not query:
            if str(results) in tabs.tabs():tabs.forget(results)
            if previous[0] in tabs.tabs():tabs.select(previous[0])
            return
        if str(results) not in tabs.tabs():previous[0]=tabs.select();tabs.add(results,text='Search results')
        # A scrolling list keeps broad queries usable at the minimum window size.
        for widget in results.winfo_children():widget.destroy()
        listing=tk.Listbox(results,font=('Segoe UI',12),exportselection=False)
        matches=[tool for tool in all_tools if query in ' '.join(tool[:3]).casefold()]
        for category,name,description,_ in matches:listing.insert('end',f'{category}  /  {name} — {description}')
        scroll=ttk.Scrollbar(results,command=listing.yview);scroll.pack(side='right',fill='y')
        listing.config(yscrollcommand=scroll.set);listing.pack(fill='both',expand=True)
        def open_selected(_=None):
            if listing.curselection():matches[listing.curselection()[0]][3]()
        listing.bind('<Double-1>',open_selected);listing.bind('<Return>',open_selected)
        ttk.Button(results,text='Open selected editor',command=open_selected).pack(anchor='w',pady=8)
        if not matches:listing.insert('end','No matching editors.')
        tabs.select(results)
    search.trace_add('write',filter_tools)
    return home
