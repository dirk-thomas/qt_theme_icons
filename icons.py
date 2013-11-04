#!/usr/bin/env python

import signal
import sys
from types import MethodType

from PyQt4.QtCore import QSignalMapper, Qt, QTimer
from PyQt4.QtGui import QAbstractItemView, QAction, QApplication, QIcon, QKeySequence, QLineEdit, QMainWindow, QSortFilterProxyModel, QStandardItem, QStandardItemModel, QTableView, QToolBar

def main(icon_spec):
    app = QApplication(sys.argv)

    main_window = QMainWindow()

    def sigint_handler(*args):
        main_window.close()
    signal.signal(signal.SIGINT, sigint_handler)
    # the timer enables triggering the sigint_handler
    signal_timer = QTimer()
    signal_timer.start(100)
    signal_timer.timeout.connect(lambda: None)

    tool_bar = QToolBar()
    main_window.addToolBar(Qt.TopToolBarArea, tool_bar)

    table_view = QTableView()
    table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
    table_view.setSelectionMode(QAbstractItemView.SingleSelection)
    table_view.setSortingEnabled(True)
    main_window.setCentralWidget(table_view)

    proxy_model = QSortFilterProxyModel()
    proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
    proxy_model.setFilterKeyColumn(1)
    table_view.setModel(proxy_model)
    proxy_model.layoutChanged.connect(table_view.resizeRowsToContents)

    item_model = QStandardItemModel()
    proxy_model.setSourceModel(item_model)

    # get all icons and their available sizes
    icons = []
    all_sizes = set([])
    for context, icon_names in icon_spec:
        for icon_name in icon_names:
            icon = QIcon.fromTheme(icon_name)
            sizes = []
            for size in icon.availableSizes():
                size = (size.width(), size.height())
                sizes.append(size)
                all_sizes.add(size)
            sizes.sort()
            icons.append({
                'context': context,
                'icon_name': icon_name,
                'icon': icon,
                'sizes': sizes,
            })
    all_sizes = list(all_sizes)
    all_sizes.sort()

    # input field for filter
    def filter_changed(value):
        proxy_model.setFilterRegExp(value)
        table_view.resizeRowsToContents()
    filter_line_edit = QLineEdit()
    filter_line_edit.setMaximumWidth(200)
    filter_line_edit.setPlaceholderText('Filter name')
    filter_line_edit.setToolTip('Filter name optionally using regular expressions (' + QKeySequence(QKeySequence.Find).toString() + ')')
    filter_line_edit.textChanged.connect(filter_changed)
    tool_bar.addWidget(filter_line_edit)

    # actions to toggle visibility of available sizes/columns 
    def action_toggled(index):
        column = 2 + index
        table_view.setColumnHidden(column, not table_view.isColumnHidden(column))
        table_view.resizeColumnsToContents()
        table_view.resizeRowsToContents()
    signal_mapper = QSignalMapper()
    for i, size in enumerate(all_sizes):
        action = QAction('%dx%d' % size, tool_bar)
        action.setCheckable(True)
        action.setChecked(True)
        tool_bar.addAction(action)
        action.toggled.connect(signal_mapper.map)
        signal_mapper.setMapping(action, i)
        # set tool tip and handle key sequence
        tool_tip = 'Toggle visibility of column'
        if i < 10:
            digit = ('%d' % (i + 1))[-1]
            tool_tip += ' (%s)' % QKeySequence('Ctrl+%s' % digit).toString()
        action.setToolTip(tool_tip)
    signal_mapper.mapped.connect(action_toggled)

    # label columns
    header_labels = ['context', 'name']
    for width, height in all_sizes:
        header_labels.append('%dx%d' % (width, height))
    item_model.setColumnCount(len(header_labels))
    item_model.setHorizontalHeaderLabels(header_labels)

    # fill rows
    item_model.setRowCount(len(icons))
    for row, icon_data in enumerate(icons):
        # context
        item = QStandardItem(icon_data['context'])
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        item_model.setItem(row, 0, item)
        # icon name
        item = QStandardItem(icon_data['icon_name'])
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        item_model.setItem(row, 1, item)
        for index_in_all_sizes, size in enumerate(all_sizes):
            column = 2 + index_in_all_sizes
            if size in icon_data['sizes']:
                # icon as pixmap to keep specific size
                item = QStandardItem('')
                pixmap = icon_data['icon'].pixmap(size[0], size[1])
                item.setData(pixmap, Qt.DecorationRole)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                item_model.setItem(row, column, item)
            else:
                # single space to be sortable against icons
                item = QStandardItem(' ')
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                item_model.setItem(row, column, item)

    table_view.resizeColumnsToContents()
    # manually set row heights because resizeRowsToContents is not working properly
    for row, icon_data in enumerate(icons):
        if len(icon_data['sizes']) > 0:
            max_size = icon_data['sizes'][-1]
            table_view.setRowHeight(row, max_size[1])

    # enable focus find (ctrl+f) and toggle columns (ctrl+NUM)
    def main_window_keyPressEvent(self, event, old_keyPressEvent=QMainWindow.keyPressEvent):
        if event.matches(QKeySequence.Find):
            filter_line_edit.setFocus()
            return
        if event.modifiers() == Qt.ControlModifier and event.key() >= Qt.Key_0 and event.key() <= Qt.Key_9:
            index = event.key() - Qt.Key_1
            if event.key() == Qt.Key_0:
                index += 10
            action = signal_mapper.mapping(index)
            if action:
                action.toggle()
                return
        old_keyPressEvent(self, event)
    main_window.keyPressEvent = MethodType(main_window_keyPressEvent, table_view)

    # enable copy (ctrl+c) name of icon to clipboard
    def table_view_keyPressEvent(self, event, old_keyPressEvent=QTableView.keyPressEvent):
        if event.matches(QKeySequence.Copy):
            selection_model = self.selectionModel()
            if selection_model.hasSelection():
                index = selection_model.selectedRows()[0]
                source_index = self.model().mapToSource(index)
                item = self.model().sourceModel().item(source_index.row(), 1)
                icon_name = item.data(Qt.EditRole)
                app.clipboard().setText(icon_name.toString())
                return
        old_keyPressEvent(self, event)
    table_view.keyPressEvent = MethodType(table_view_keyPressEvent, table_view)

    main_window.showMaximized()
    return app.exec_()

# icon naming specification http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
icon_spec = []
icon_spec.append(('actions', [
    'address-book-new',
    'application-exit',
    'appointment-new',
    'call-start',
    'call-stop',
    'contact-new',
    'document-new',
    'document-open',
    'document-open-recent',
    'document-page-setup',
    'document-print',
    'document-print-preview',
    'document-properties',
    'document-revert',
    'document-save',
    'document-save-as',
    'document-send',
    'edit-clear',
    'edit-copy',
    'edit-cut',
    'edit-delete',
    'edit-find',
    'edit-find-replace',
    'edit-paste',
    'edit-redo',
    'edit-select-all',
    'edit-undo',
    'folder-new',
    'format-indent-less',
    'format-indent-more',
    'format-justify-center',
    'format-justify-fill',
    'format-justify-left',
    'format-justify-right',
    'format-text-direction-ltr',
    'format-text-direction-rtl',
    'format-text-bold',
    'format-text-italic',
    'format-text-underline',
    'format-text-strikethrough',
    'go-bottom',
    'go-down',
    'go-first',
    'go-home',
    'go-jump',
    'go-last',
    'go-next',
    'go-previous',
    'go-top',
    'go-up',
    'help-about',
    'help-contents',
    'help-faq',
    'insert-image',
    'insert-link',
    'insert-object',
    'insert-text',
    'list-add',
    'list-remove',
    'mail-forward',
    'mail-mark-important',
    'mail-mark-junk',
    'mail-mark-notjunk',
    'mail-mark-read',
    'mail-mark-unread',
    'mail-message-new',
    'mail-reply-all',
    'mail-reply-sender',
    'mail-send',
    'mail-send-receive',
    'media-eject',
    'media-playback-pause',
    'media-playback-start',
    'media-playback-stop',
    'media-record',
    'media-seek-backward',
    'media-seek-forward',
    'media-skip-backward',
    'media-skip-forward',
    'object-flip-horizontal',
    'object-flip-vertical',
    'object-rotate-left',
    'object-rotate-right',
    'process-stop',
    'system-lock-screen',
    'system-log-out',
    'system-run',
    'system-search',
    'system-reboot',
    'system-shutdown',
    'tools-check-spelling',
    'view-fullscreen',
    'view-refresh',
    'view-restore',
    'view-sort-ascending',
    'view-sort-descending',
    'window-close',
    'window-new',
    'zoom-fit-best',
    'zoom-in',
    'zoom-original',
    'zoom-out',
]))
icon_spec.append(('animations', [
    'process-working',
]))
icon_spec.append(('apps', [
    'accessories-calculator',
    'accessories-character-map',
    'accessories-dictionary',
    'accessories-text-editor',
    'help-browser',
    'multimedia-volume-control',
    'preferences-desktop-accessibility',
    'preferences-desktop-font',
    'preferences-desktop-keyboard',
    'preferences-desktop-locale',
    'preferences-desktop-multimedia',
    'preferences-desktop-screensaver',
    'preferences-desktop-theme',
    'preferences-desktop-wallpaper',
    'system-file-manager',
    'system-software-install',
    'system-software-update',
    'utilities-system-monitor',
    'utilities-terminal',
]))
icon_spec.append(('categories', [
    'applications-accessories',
    'applications-development',
    'applications-engineering',
    'applications-games',
    'applications-graphics',
    'applications-internet',
    'applications-multimedia',
    'applications-office',
    'applications-other',
    'applications-science',
    'applications-system',
    'applications-utilities',
    'preferences-desktop',
    'preferences-desktop-peripherals',
    'preferences-desktop-personal',
    'preferences-other',
    'preferences-system',
    'preferences-system-network',
    'system-help',
]))
icon_spec.append(('devices', [
    'audio-card',
    'audio-input-microphone',
    'battery',
    'camera-photo',
    'camera-video',
    'camera-web',
    'computer',
    'drive-harddisk',
    'drive-optical',
    'drive-removable-media',
    'input-gaming',
    'input-keyboard',
    'input-mouse',
    'input-tablet',
    'media-flash',
    'media-floppy',
    'media-optical',
    'media-tape',
    'modem',
    'multimedia-player',
    'network-wired',
    'network-wireless',
    'pda',
    'phone',
    'printer',
    'scanner',
    'video-display',
]))
icon_spec.append(('emblems', [
    'emblem-default',
    'emblem-documents',
    'emblem-downloads',
    'emblem-favorite',
    'emblem-important',
    'emblem-mail',
    'emblem-photos',
    'emblem-readonly',
    'emblem-shared',
    'emblem-symbolic-link',
    'emblem-synchronized',
    'emblem-system',
    'emblem-unreadable',
]))
icon_spec.append(('emotions', [
    'face-angel',
    'face-angry',
    'face-cool',
    'face-crying',
    'face-devilish',
    'face-embarrassed',
    'face-kiss',
    'face-laugh',
    'face-monkey',
    'face-plain',
    'face-raspberry',
    'face-sad',
    'face-sick',
    'face-smile',
    'face-smile-big',
    'face-smirk',
    'face-surprise',
    'face-tired',
    'face-uncertain',
    'face-wink',
    'face-worried',
]))
#is_3166_1_alpha_2 = ['ad', 'ae', 'af', 'ag', 'ai', 'al', 'am', 'ao', 'aq', 'ar', 'as', 'at', 'au', 'aw', 'ax', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg', 'bh', 'bi', 'bj', 'bl', 'bm', 'bn', 'bo', 'bq', 'br', 'bs', 'bt', 'bv', 'bw', 'by', 'bz', 'ca', 'cc', 'cd', 'cf', 'cg', 'ch', 'ci', 'ck', 'cl', 'cm', 'cn', 'co', 'cr', 'cu', 'cv', 'cw', 'cx', 'cy', 'cz', 'de', 'dj', 'dk', 'dm', 'do', 'dz', 'ec', 'ee', 'eg', 'eh', 'er', 'es', 'et', 'fi', 'fj', 'fk', 'fm', 'fo', 'fr', 'ga', 'gb', 'gd', 'ge', 'gf', 'gg', 'gh', 'gi', 'gl', 'gm', 'gn', 'gp', 'gq', 'gr', 'gs', 'gt', 'gu', 'gw', 'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu', 'id', 'ie', 'il', 'im', 'in', 'io', 'iq', 'ir', 'is', 'it', 'je', 'jm', 'jo', 'jp', 'ke', 'kg', 'kh', 'ki', 'km', 'kn', 'kp', 'kr', 'kw', 'ky', 'kz', 'la', 'lb', 'lc', 'li', 'lk', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'mc', 'md', 'me', 'mf', 'mg', 'mh', 'mk', 'ml', 'mm', 'mn', 'mo', 'mp', 'mq', 'mr', 'ms', 'mt', 'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'nc', 'ne', 'nf', 'ng', 'ni', 'nl', 'no', 'np', 'nr', 'nu', 'nz', 'om', 'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl', 'pm', 'pn', 'pr', 'ps', 'pt', 'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'sa', 'sb', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sj', 'sk', 'sl', 'sm', 'sn', 'so', 'sr', 'ss', 'st', 'sv', 'sx', 'sy', 'sz', 'tc', 'td', 'tf', 'tg', 'th', 'tj', 'tk', 'tl', 'tm', 'tn', 'to', 'tr', 'tt', 'tv', 'tw', 'tz', 'ua', 'ug', 'um', 'us', 'uy', 'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn', 'vu', 'wf', 'ws', 'ye', 'yt', 'za', 'zm', 'zw']
#flags = []
#for code in is_3166_1_alpha_2:
#    flags.append('flag-%s' % code)
#icon_spec.append(('intl', flags))
icon_spec.append(('mimetypes', [
    # 
    'application-x-executable',
    'audio-x-generic',
    'font-x-generic',
    'image-x-generic',
    'package-x-generic',
    'text-html',
    'text-x-generic',
    'text-x-generic-template',
    'text-x-script',
    'video-x-generic',
    'x-office-address-book',
    'x-office-calendar',
    'x-office-document',
    'x-office-presentation',
    'x-office-spreadsheet',
]))
icon_spec.append(('places', [
    'folder',
    'folder-remote',
    'network-server',
    'network-workgroup',
    'start-here',
    'user-bookmarks',
    'user-desktop',
    'user-home',
    'user-trash',
]))
icon_spec.append(('status', [
    'appointment-missed',
    'appointment-soon',
    'audio-volume-high',
    'audio-volume-low',
    'audio-volume-medium',
    'audio-volume-muted',
    'battery-caution',
    'battery-low',
    'dialog-error',
    'dialog-information',
    'dialog-password',
    'dialog-question',
    'dialog-warning',
    'folder-drag-accept',
    'folder-open',
    'folder-visiting',
    'image-loading',
    'image-missing',
    'mail-attachment',
    'mail-unread',
    'mail-read',
    'mail-replied',
    'mail-signed',
    'mail-signed-verified',
    'media-playlist-repeat',
    'media-playlist-shuffle',
    'network-error',
    'network-idle',
    'network-offline',
    'network-receive',
    'network-transmit',
    'network-transmit-receive',
    'printer-error',
    'printer-printing',
    'security-high',
    'security-medium',
    'security-low',
    'software-update-available',
    'software-update-urgent',
    'sync-error',
    'sync-synchronizing',
    'task-due',
    'task-past-due',
    'user-available',
    'user-away',
    'user-idle',
    'user-offline',
    'user-trash-full',
    'weather-clear',
    'weather-clear-night',
    'weather-few-clouds',
    'weather-few-clouds-night',
    'weather-fog',
    'weather-overcast',
    'weather-severe-alert',
    'weather-showers',
    'weather-showers-scattered',
    'weather-snow',
    'weather-storm',
]))

if __name__ == '__main__':
    sys.exit(main(icon_spec))
