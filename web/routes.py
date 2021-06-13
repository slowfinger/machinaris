
import pytz
import os
import time

from datetime import datetime
from flask import Flask, flash, redirect, render_template, \
        request, session, url_for, send_from_directory, make_response

from common.config import globals
from web import app, utils
from web.actions import chia, plotman, chiadog, worker

@app.route('/')
def landing():
    gc = globals.load()
    if not globals.is_setup():
        return redirect(url_for('setup'))
    return render_template('landing.html')

@app.route('/index')
def index():
    gc = globals.load()
    if not globals.is_setup():
        return redirect(url_for('setup'))
    if not utils.is_controller():
        return redirect(url_for('controller'))
    workers = worker.load_worker_summary()
    farming = chia.load_farm_summary()
    plotting = plotman.load_plotting_summary()
    challenges = chia.recent_challenges()
    return render_template('index.html', reload_seconds=60, farming=farming.__dict__, \
        plotting=plotting.__dict__, challenges=challenges, workers=workers, global_config=gc)

@app.route('/views/challenges')
def views_challenges():
    challenges = chia.recent_challenges()
    return render_template('views/challenges.html', challenges=challenges)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    key_paths = globals.get_key_paths()
    app.logger.info("Setup found these key paths: {0}".format(key_paths))
    show_setup = True
    if request.method == 'POST':
        show_setup = not chia.generate_key(key_paths[0])
    if show_setup:
        return render_template('setup.html', key_paths = key_paths)
    else:
        return redirect(url_for('index'))

@app.route('/controller')
def controller():
    return render_template('controller.html', controller_url = utils.get_controller_url())

@app.route('/plotting', methods=['GET', 'POST'])
def plotting():
    gc = globals.load()
    if request.method == 'POST':
        app.logger.info("Form submitted: {0}".format(request.form))
        if request.form.get('action') == 'start':
            plotman.start_plotman()
        elif request.form.get('action') == 'stop':
            plotman.stop_plotman()
        elif request.form.get('action') in ['suspend', 'resume', 'kill']:
            plotman.action_plots(request.form)
        else:
            app.logger.info("Unknown plotting form: {0}".format(request.form))
    plotters = plotman.load_plotters()
    plotting = plotman.load_plotting_summary()
    return render_template('plotting.html', reload_seconds=60,  plotting=plotting, 
        plotters=plotters, global_config=gc)

@app.route('/farming')
def farming():
    if request.args.get('analyze'):  # Xhr with a plot filename
        return plotman.analyze(request.args.get('analyze'))
    elif request.args.get('check'):  # Xhr calling for check output
        return chia.check_plots(request.args.get('first_load'))
    gc = globals.load()
    
    farming = chia.load_farm_summary()
    plots = chia.load_plots_farming()
    chia.compare_plot_counts(gc, farming, plots)
    return render_template('farming.html', farming=farming, plots=plots, 
        global_config=gc)

@app.route('/plots_check')
def plots_check():
    return render_template('plots_check.html')

@app.route('/alerts', methods=['GET', 'POST'])
def alerts():
    gc = globals.load()
    if request.method == 'POST':
        app.logger.info("Form submitted: {0}".format(request.form))
        if request.form.get('action') == 'start':
            chiadog_cli.start_chiadog()
        elif request.form.get('action') == 'stop':
            chiadog_cli.stop_chiadog()
        else:
            app.logger.info("Unknown alerts form: {0}".format(request.form))
    notifications = chiadog.get_notifications()
    return render_template('alerts.html', chiadog_running = chiadog.get_chiadog_pid(),
        reload_seconds=60, notifications=notifications, global_config=gc)

@app.route('/wallet')    
def wallet():
    gc = globals.load()
    wallets = chia.load_wallets()
    return render_template('wallet.html', wallets=wallets, 
        global_config=gc)

@app.route('/keys')
def keys():
    gc = globals.load()
    keys = chia.load_keys_show()
    key_paths = globals.get_key_paths()
    return render_template('keys.html', keys=keys, 
        key_paths=key_paths, global_config=gc)

@app.route('/network/blockchain')
def network_blockchain():
    gc = globals.load()
    blockchains = chia.load_blockchain_show()
    return render_template('network/blockchain.html', reload_seconds=60, 
        blockchains=blockchains, global_config=gc, now=gc['now'])

@app.route('/network/connections', methods=['GET', 'POST'])
def network_connections():
    gc = globals.load()
    if request.method == 'POST':
        if request.form.get('action') == "add":
            chia.add_connection(request.form.get("connection"))
        else:
            app.logger.info("Unknown form action: {0}".format(request.form))
    connections = chia.load_connections_show()
    return render_template('network/connections.html', reload_seconds=60, 
        connections=connections, global_config=gc, now=gc['now'])

@app.route('/settings/plotting', methods=['GET', 'POST'])
def settings_plotting():
    gc = globals.load()
    if request.method == 'POST':
        plotman.save_config( \
            worker.get_worker_by_hostname(request.form.get('worker')), \
            request.form.get("config")
        )
    workers = worker.load_worker_summary()
    selected_worker = workers.farmers[0]
    return render_template('settings/plotting.html',
        workers=workers.farmers, selected_worker=selected_worker, global_config=gc)

@app.route('/settings/farming', methods=['GET', 'POST'])
def settings_farming():
    gc = globals.load()
    if request.method == 'POST':
        chia.save_config( \
            worker.get_worker_by_hostname(request.form.get('worker')), \
            request.form.get("config")
        )
    workers = worker.load_worker_summary()
    selected_worker = workers.farmers[0]
    return render_template('settings/farming.html',
        workers=workers.farmers, selected_worker=selected_worker, global_config=gc)

@app.route('/settings/alerts', methods=['GET', 'POST'])
def settings_alerts():
    gc = globals.load()
    if request.method == 'POST':
        chiadog.save_config( \
            worker.get_worker_by_hostname(request.form.get('worker')), \
            request.form.get("config")
        )
    workers = worker.load_worker_summary()
    selected_worker = workers.farmers[0]
    return render_template('settings/alerts.html',
        workers=workers.farmers, selected_worker=selected_worker, global_config=gc)

@app.route('/settings/config')
def views_settings_config():
    w = worker.get_worker_by_hostname(request.args.get('worker'))
    config_type = request.args.get('type')
    if config_type == "alerts":
        response = make_response(chiadog.load_config(w), 200)
    elif config_type == "farming":
        response = make_response(chia.load_config(w), 200)
    elif config_type == "plotting":
        response = make_response(plotman.load_config(w), 200)
    else:
        abort("Unsupported config type: {0}".format(config_type), 400)
    response.mimetype = "application/x-yaml"
    return response

@app.route('/logs')
def logs():
    return render_template('logs.html')

@app.route('/logfile')
def logfile():
    log_file = None
    log_type = request.args.get("log")
    if log_type in [ 'alerts', 'farming', 'plotting']:
        log_id = request.args.get("log_id")
        return log_parser.get_log_lines(log_type, log_id)
    else:
        abort(500, "Unsupported log type: {0}".format(log_type))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
            'favicon.ico', mimetype='image/vnd.microsoft.icon')