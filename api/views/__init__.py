from . import actions
from . import alerts
from . import blockchains
from . import challenges
from . import configs
from . import connections
from . import farms
from . import keys
from . import plots
from . import plottings
from . import wallets
from . import workers


MODULES = (
    actions,
    alerts,
    blockchains,
    challenges,
    configs,
    connections,
    farms,
    keys,
    plots,
    plottings,
    wallets,
    workers,
)


def register_blueprints(api):
    for module in MODULES:
        api.register_blueprint(module.blp)