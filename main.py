from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.graphics import Line, Color, Ellipse, Rectangle
from kivy.clock import Clock
from datetime import datetime, timedelta
import json
import os

class Child:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight
        self.temperature_log = []
        self.medication_log = []
    
    def calculate_paracetamol_dose(self):
        single_dose = round(self.weight * 12.5, 1)
        max_daily = round(self.weight * 60, 1)
        return single_dose, max_daily
    
    def calculate_ibuprofen_dose(self):
        single_dose = round(self.weight * 7.5, 1)
        max_daily = round(self.weight * 30, 1)
        return single_dose, max_daily
    
    def can_take_medication(self, med_type):
        now = datetime.now()
        for log in reversed(self.medication_log):
            if log['type'] == med_type:
                time_diff = now - datetime.fromisoformat(log['time'])
                min_interval = 6 if med_type == 'paracetamol' else 8
                if time_diff < timedelta(hours=min_interval):
                    return False, min_interval - time_diff.total_seconds() / 3600
        return True, 0
    
    def to_dict(self):
        return {
            'name': self.name,
            'weight': self.weight,
            'temperature_log': [{'time': t['time'].isoformat(), 'value': t['value']} for t in self.temperature_log],
            'medication_log': [{'time': m['time'].isoformat(), 'type': m['type'], 'dose': m['dose']} for m in self.medication_log]
        }
    
    @classmethod
    def from_dict(cls, data):
        child = cls(data['name'], data['weight'])
        child.temperature_log = [{'time': datetime.fromisoformat(t['time']), 'value': t['value']} for t in data['temperature_log']]
        child.medication_log = [{'time': datetime.fromisoformat(m['time']), 'type': m['type'], 'dose': m['dose']} for m in data['medication_log']]
        return child

class GraphWidget(Widget):
    def __init__(self, child, **kwargs):
        super().__init__(**kwargs)
        self.child = child
        self.bind(size=self.update_graph, pos=self.update_graph)
    
    def update_graph(self, *args):
        self.canvas.clear()
        
        with self.canvas:
            # Фон графика
            Color(0.94, 0.97, 1, 1)  # Светло-голубой фон
            Rectangle(pos=self.pos, size=self.size)
            
            if not self.child.temperature_log:
                Color(0.53, 0.81, 0.92, 1)  # Небесно-голубой
                # Текст "Нет данных" будет добавлен позже
                return
            
            temps = self.child.temperature_log[-24:]
            if len(temps) < 1:
                return
            
            margin = 40
            width = self.width - 2 * margin
            height = self.height - 2 * margin
            
            # Масштабирование
            min_temp = min(t['value'] for t in temps)
            max_temp = max(t['value'] for t in temps)
            temp_range = max(max_temp - min_temp, 1)
            
            # Оси
            Color(0.29, 0.56, 0.64, 1)  # Морская волна
            Line(points=[margin, margin + height, margin + width, margin + height], width=2)
            Line(points=[margin, margin, margin, margin + height], width=2)
            
            # Сетка температур
            Color(0.69, 0.88, 0.90, 0.5)  # Полупрозрачная сетка
            for temp in range(int(min_temp), int(max_temp) + 2):
                if temp >= 35 and temp <= 42:
                    y = self.y + margin + height - ((temp - min_temp) / temp_range) * height
                    Line(points=[self.x + margin, y, self.x + margin + width, y], width=1)
            
            # Линия температуры
            if len(temps) > 1:
                Color(1, 0.5, 0.5, 1)  # Коралловый
                points = []
                for i, temp in enumerate(temps):
                    x = self.x + margin + (i / (len(temps) - 1)) * width
                    y = self.y + margin + height - ((temp['value'] - min_temp) / temp_range) * height
                    points.extend([x, y])
                
                Line(points=points, width=3)
            
            # Точки температуры
            for i, temp in enumerate(temps):
                x = self.x + margin + (i / (len(temps) - 1) if len(temps) > 1 else 0.5) * width
                y = self.y + margin + height - ((temp['value'] - min_temp) / temp_range) * height
                
                # Красивая точка
                Color(1, 0.5, 0.5, 1)  # Коралловый
                Ellipse(pos=(x-6, y-6), size=(12, 12))
                Color(1, 1, 1, 1)  # Белый центр
                Ellipse(pos=(x-3, y-3), size=(6, 6))
            
            # Отметки лекарств (только эмодзи, без треугольников)
            for med in self.child.medication_log:
                med_time = datetime.fromisoformat(med['time'])
                
                # Находим ближайшую точку температуры
                closest_temp_index = -1
                min_time_diff = float('inf')
                
                for i, temp in enumerate(temps):
                    temp_time = datetime.fromisoformat(temp['time'])
                    time_diff = abs((med_time - temp_time).total_seconds())
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        closest_temp_index = i
                
                if closest_temp_index != -1 and min_time_diff < 1800:  # 30 минут
                    x = self.x + margin + (closest_temp_index / (len(temps) - 1) if len(temps) > 1 else 0.5) * width
                    temp_value = temps[closest_temp_index]['value']
                    y = self.y + margin + height - ((temp_value - min_temp) / temp_range) * height
                    
                    # Только эмодзи (поднимаем выше)
                    if med['type'] == 'paracetamol':
                        Color(1, 0.55, 0.41, 1)  # Оранжевый
                    else:
                        Color(0.29, 0.56, 0.64, 1)  # Синий
                    
                    # Здесь будет эмодзи (в Kivy сложно с эмодзи, используем цветные круги)
                    if med['type'] == 'paracetamol':
                        Color(1, 0.55, 0.41, 1)
                        Ellipse(pos=(x-8, y-45), size=(16, 16))  # Оранжевый круг
                    else:
                        Color(0.29, 0.56, 0.64, 1)
                        Rectangle(pos=(x-8, y-45), size=(16, 16))  # Синий квадрат

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.children_data = []
        self.load_data()
        
        # Создаем фон
        with self.canvas.before:
            Color(0.91, 0.96, 0.97, 1)  # Нежно-голубой фон
            self.rect = Rectangle(size=self.size, pos=self.pos)
        
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        
        # Заголовок
        title = Label(text='Калькулятор жаропонижающих', 
                     font_size='28sp', size_hint_y=None, height='80dp',
                     color=(0.29, 0.56, 0.64, 1), bold=True)
        layout.add_widget(title)
        
        # Поля ввода
        input_layout = BoxLayout(orientation='vertical', size_hint_y=None, height='220dp', spacing=15)
        
        name_label = Label(text='Имя ребенка:', size_hint_y=None, height='30dp',
                          color=(0.18, 0.31, 0.31, 1), font_size='16sp', halign='left')
        input_layout.add_widget(name_label)
        
        self.name_input = TextInput(hint_text='Введите имя ребенка', size_hint_y=None, height='50dp',
                                   background_color=(0.97, 0.98, 1, 1),
                                   foreground_color=(0.18, 0.31, 0.31, 1),
                                   font_size='16sp', multiline=False)
        input_layout.add_widget(self.name_input)
        
        weight_label = Label(text='Вес (кг):', size_hint_y=None, height='30dp',
                            color=(0.18, 0.31, 0.31, 1), font_size='16sp', halign='left')
        input_layout.add_widget(weight_label)
        
        self.weight_input = TextInput(hint_text='Введите вес в килограммах', size_hint_y=None, height='50dp',
                                     background_color=(0.97, 0.98, 1, 1),
                                     foreground_color=(0.18, 0.31, 0.31, 1),
                                     font_size='16sp', multiline=False)
        input_layout.add_widget(self.weight_input)
        
        create_btn = Button(text='Создать карточку', size_hint_y=None, height='60dp',
                           background_color=(0.29, 0.56, 0.64, 1),
                           color=(1, 1, 1, 1), font_size='18sp', bold=True)
        create_btn.bind(on_press=self.create_child)
        input_layout.add_widget(create_btn)
        
        layout.add_widget(input_layout)
        
        # Список детей
        children_label = Label(text='Мои дети:', font_size='20sp', 
                              size_hint_y=None, height='50dp',
                              color=(0.29, 0.56, 0.64, 1), bold=True, halign='left')
        layout.add_widget(children_label)
        
        # Скроллируемый список
        scroll = ScrollView()
        self.children_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        self.children_layout.bind(minimum_height=self.children_layout.setter('height'))
        
        scroll.add_widget(self.children_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        self.refresh_children_list()
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def create_child(self, instance):
        name = self.name_input.text.strip()
        weight = self.weight_input.text.strip().replace(',', '.')
        
        if not name or not weight:
            self.show_popup('Ошибка', 'Заполните все поля')
            return
        
        try:
            weight_float = float(weight)
            if weight_float <= 0:
                raise ValueError()
        except ValueError:
            self.show_popup('Ошибка', 'Введите корректный вес')
            return
        
        child = Child(name, weight_float)
        self.children_data.append(child)
        self.save_data()
        self.refresh_children_list()
        
        self.name_input.text = ''
        self.weight_input.text = ''
        self.show_popup('Успех', f'Карточка {name} создана!')
    
    def refresh_children_list(self):
        self.children_layout.clear_widgets()
        
        for child in self.children_data:
            child_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='70dp', spacing=15)
            
            # Фон для карточки ребенка
            with child_layout.canvas.before:
                Color(0.53, 0.81, 0.92, 1)  # Небесно-голубой
                child_layout.rect = Rectangle(size=child_layout.size, pos=child_layout.pos)
            
            child_layout.bind(size=lambda instance, value: setattr(instance.rect, 'size', value),
                             pos=lambda instance, value: setattr(instance.rect, 'pos', value))
            
            child_btn = Button(text=f'{child.name} ({child.weight} кг)',
                              background_color=(0, 0, 0, 0),  # Прозрачный
                              color=(0.18, 0.31, 0.31, 1),
                              font_size='16sp', bold=True)
            child_btn.bind(on_press=lambda x, c=child: self.open_child_screen(c))
            
            delete_btn = Button(text='X', size_hint_x=None, width='60dp',
                               background_color=(1, 0.5, 0.5, 1),
                               color=(1, 1, 1, 1), font_size='18sp', bold=True)
            delete_btn.bind(on_press=lambda x, c=child: self.delete_child(c))
            
            child_layout.add_widget(child_btn)
            child_layout.add_widget(delete_btn)
            
            self.children_layout.add_widget(child_layout)
    
    def delete_child(self, child):
        self.children_data.remove(child)
        self.save_data()
        self.refresh_children_list()
        self.show_popup('Удалено', f'Карточка {child.name} удалена')
    
    def open_child_screen(self, child):
        app = App.get_running_app()
        child_screen = ChildScreen(child=child, name=f'child_{id(child)}')
        app.root.add_widget(child_screen)
        app.root.current = child_screen.name
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(Label(text=message, font_size='16sp', 
                                color=(0.18, 0.31, 0.31, 1)))
        
        close_btn = Button(text='OK', size_hint_y=None, height='50dp',
                          background_color=(0.29, 0.56, 0.64, 1),
                          color=(1, 1, 1, 1), font_size='16sp')
        
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.5))
        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()
    
    def save_data(self):
        try:
            data = [child.to_dict() for child in self.children_data]
            with open('fever_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_data(self):
        try:
            if os.path.exists('fever_data.json'):
                with open('fever_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.children_data = [Child.from_dict(child_data) for child_data in data]
        except:
            self.children_data = []

class ChildScreen(Screen):
    def __init__(self, child, **kwargs):
        super().__init__(**kwargs)
        self.child = child
        
        # Фон экрана
        with self.canvas.before:
            Color(0.91, 0.96, 0.97, 1)  # Нежно-голубой
            self.rect = Rectangle(size=self.size, pos=self.pos)
        
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Кнопка назад
        back_btn = Button(text='← Назад', size_hint_y=None, height='60dp',
                         background_color=(0.29, 0.56, 0.64, 1),
                         color=(1, 1, 1, 1), font_size='18sp', bold=True)
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        # Информация о ребенке с кнопкой редактирования
        info_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='70dp', spacing=15)
        
        self.info_label = Label(text=f'{child.name}, {child.weight} кг',
                               font_size='26sp', color=(0.29, 0.56, 0.64, 1), bold=True)
        edit_btn = Button(text='✏️', size_hint_x=None, width='60dp',
                         background_color=(0.53, 0.81, 0.92, 1),
                         color=(0.18, 0.31, 0.31, 1), font_size='20sp', bold=True)
        edit_btn.bind(on_press=self.edit_child)
        
        info_layout.add_widget(self.info_label)
        info_layout.add_widget(edit_btn)
        layout.add_widget(info_layout)
        
        # График
        graph_label = Label(text='График температуры', font_size='18sp',
                           size_hint_y=None, height='40dp',
                           color=(0.18, 0.31, 0.31, 1), bold=True)
        layout.add_widget(graph_label)
        
        self.graph = GraphWidget(child, size_hint_y=None, height='250dp')
        layout.add_widget(self.graph)
        
        # Дата
        date_label = Label(text=datetime.now().strftime('%d.%m.%Y'),
                          font_size='14sp', size_hint_y=None, height='30dp',
                          color=(0.29, 0.56, 0.64, 1))
        layout.add_widget(date_label)
        
        # Температура
        temp_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=15)
        
        self.temp_input = TextInput(hint_text='Температура °C', size_hint_x=0.7,
                                   background_color=(0.97, 0.98, 1, 1),
                                   foreground_color=(0.18, 0.31, 0.31, 1),
                                   font_size='16sp', multiline=False)
        temp_btn = Button(text='Записать', size_hint_x=0.3,
                         background_color=(1, 0.5, 0.5, 1),
                         color=(1, 1, 1, 1), font_size='16sp', bold=True)
        temp_btn.bind(on_press=self.add_temperature)
        
        temp_layout.add_widget(self.temp_input)
        temp_layout.add_widget(temp_btn)
        layout.add_widget(temp_layout)
        
        # Дозировки
        para_dose, para_max = child.calculate_paracetamol_dose()
        ibu_dose, ibu_max = child.calculate_ibuprofen_dose()
        
        dose_layout = BoxLayout(orientation='vertical', size_hint_y=None, height='200dp', spacing=10)
        
        para_label = Label(text=f'Парацетамол: {para_dose} мг (макс. {para_max} мг/сутки)',
                          size_hint_y=None, height='40dp',
                          color=(0.18, 0.31, 0.31, 1), font_size='14sp')
        para_btn = Button(text='Дать парацетамол', size_hint_y=None, height='60dp',
                         background_color=(1, 0.55, 0.41, 1),
                         color=(1, 1, 1, 1), font_size='16sp', bold=True)
        para_btn.bind(on_press=lambda x: self.give_medication('paracetamol', para_dose))
        
        ibu_label = Label(text=f'Ибупрофен: {ibu_dose} мг (макс. {ibu_max} мг/сутки)',
                         size_hint_y=None, height='40dp',
                         color=(0.18, 0.31, 0.31, 1), font_size='14sp')
        ibu_btn = Button(text='Дать ибупрофен', size_hint_y=None, height='60dp',
                        background_color=(0.29, 0.56, 0.64, 1),
                        color=(1, 1, 1, 1), font_size='16sp', bold=True)
        ibu_btn.bind(on_press=lambda x: self.give_medication('ibuprofen', ibu_dose))
        
        dose_layout.add_widget(para_label)
        dose_layout.add_widget(para_btn)
        dose_layout.add_widget(ibu_label)
        dose_layout.add_widget(ibu_btn)
        
        layout.add_widget(dose_layout)
        
        # История
        history_label = Label(text='История наблюдений:', font_size='18sp',
                             size_hint_y=None, height='40dp',
                             color=(0.29, 0.56, 0.64, 1), bold=True, halign='left')
        layout.add_widget(history_label)
        
        scroll = ScrollView()
        self.history_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.history_layout.bind(minimum_height=self.history_layout.setter('height'))
        
        scroll.add_widget(self.history_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        self.update_history()
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def add_temperature(self, instance):
        try:
            temp_str = self.temp_input.text.replace(',', '.')
            temp = float(temp_str)
            if not (35 <= temp <= 42):
                self.show_popup('Ошибка', 'Температура должна быть от 35 до 42°C')
                return
            
            self.child.temperature_log.append({
                'time': datetime.now(),
                'value': temp
            })
            self.temp_input.text = ''
            self.show_popup('Успех', f'Температура {temp}°C записана')
            
            self.graph.update_graph()
            self.update_history()
            self.save_data()
            
        except ValueError:
            self.show_popup('Ошибка', 'Введите корректную температуру')
    
    def give_medication(self, med_type, dose):
        can_take, wait_hours = self.child.can_take_medication(med_type)
        
        if can_take:
            self.child.medication_log.append({
                'time': datetime.now(),
                'type': med_type,
                'dose': dose
            })
            med_name = 'Парацетамол' if med_type == 'paracetamol' else 'Ибупрофен'
            self.show_popup('Успех', f'{med_name} {dose}мг дан в {datetime.now().strftime("%H:%M")}')
            
            self.graph.update_graph()
            self.update_history()
            self.save_data()
        else:
            self.show_popup('Внимание', 
                           f'Нужно подождать еще {wait_hours:.1f} часов до следующего приема')
    
    def update_history(self):
        self.history_layout.clear_widgets()
        
        all_records = []
        
        for temp in self.child.temperature_log:
            all_records.append({
                'time': temp['time'],
                'text': f"{temp['time'].strftime('%d.%m %H:%M')} - Температура: {temp['value']}°C"
            })
        
        for med in self.child.medication_log:
            med_name = 'Парацетамол' if med['type'] == 'paracetamol' else 'Ибупрофен'
            all_records.append({
                'time': med['time'],
                'text': f"{med['time'].strftime('%d.%m %H:%M')} - {med_name}: {med['dose']}мг"
            })
        
        all_records.sort(key=lambda x: x['time'], reverse=True)
        
        for record in all_records[:10]:
            label = Label(text=record['text'], size_hint_y=None, height='40dp',
                         color=(0.18, 0.31, 0.31, 1), font_size='14sp', halign='left')
            self.history_layout.add_widget(label)
    
    def go_back(self, instance):
        app = App.get_running_app()
        app.root.current = 'main'
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        content.add_widget(Label(text=message, font_size='16sp', 
                                color=(0.18, 0.31, 0.31, 1)))
        
        close_btn = Button(text='OK', size_hint_y=None, height='50dp',
                          background_color=(0.29, 0.56, 0.64, 1),
                          color=(1, 1, 1, 1), font_size='16sp', bold=True)
        
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.5))
        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()
    
    def edit_child(self, instance):
        # Создаем popup для редактирования
        content = BoxLayout(orientation='vertical', spacing=15, padding=20)
        
        content.add_widget(Label(text='Редактировать данные ребенка', 
                                font_size='18sp', size_hint_y=None, height='40dp',
                                color=(0.29, 0.56, 0.64, 1), bold=True))
        
        # Поля ввода
        name_input = TextInput(text=self.child.name, hint_text='Имя ребенка',
                              size_hint_y=None, height='50dp',
                              background_color=(0.97, 0.98, 1, 1),
                              foreground_color=(0.18, 0.31, 0.31, 1),
                              font_size='16sp', multiline=False)
        
        weight_input = TextInput(text=str(self.child.weight), hint_text='Вес (кг)',
                                size_hint_y=None, height='50dp',
                                background_color=(0.97, 0.98, 1, 1),
                                foreground_color=(0.18, 0.31, 0.31, 1),
                                font_size='16sp', multiline=False)
        
        content.add_widget(Label(text='Имя:', size_hint_y=None, height='30dp',
                                color=(0.18, 0.31, 0.31, 1), font_size='14sp'))
        content.add_widget(name_input)
        
        content.add_widget(Label(text='Вес (кг):', size_hint_y=None, height='30dp',
                                color=(0.18, 0.31, 0.31, 1), font_size='14sp'))
        content.add_widget(weight_input)
        
        # Кнопки
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=15)
        
        save_btn = Button(text='Сохранить', 
                         background_color=(0.29, 0.56, 0.64, 1),
                         color=(1, 1, 1, 1), font_size='16sp', bold=True)
        
        cancel_btn = Button(text='Отмена',
                           background_color=(1, 0.5, 0.5, 1),
                           color=(1, 1, 1, 1), font_size='16sp', bold=True)
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(title='Редактирование', content=content, size_hint=(0.9, 0.7))
        
        def save_changes(instance):
            new_name = name_input.text.strip()
            new_weight = weight_input.text.strip().replace(',', '.')
            
            if not new_name or not new_weight:
                self.show_popup('Ошибка', 'Заполните все поля')
                return
            
            try:
                weight_float = float(new_weight)
                if weight_float <= 0:
                    raise ValueError()
                
                # Сохраняем изменения
                self.child.name = new_name
                self.child.weight = weight_float
                
                # Обновляем интерфейс
                self.info_label.text = f'{new_name}, {weight_float} кг'
                
                # Обновляем дозировки
                self.update_dosages()
                
                # Сохраняем данные
                self.save_data()
                
                popup.dismiss()
                self.show_popup('Успех', 'Данные обновлены!')
                
            except ValueError:
                self.show_popup('Ошибка', 'Введите корректный вес')
        
        save_btn.bind(on_press=save_changes)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
    
    def update_dosages(self):
        # Обновляем дозировки после изменения веса
        para_dose, para_max = self.child.calculate_paracetamol_dose()
        ibu_dose, ibu_max = self.child.calculate_ibuprofen_dose()
        
        # Находим и обновляем лейблы дозировок
        for widget in self.walk():
            if isinstance(widget, Label):
                if 'Парацетамол:' in widget.text:
                    widget.text = f'Парацетамол: {para_dose} мг (макс. {para_max} мг/сутки)'
                elif 'Ибупрофен:' in widget.text:
                    widget.text = f'Ибупрофен: {ibu_dose} мг (макс. {ibu_max} мг/сутки)'
    
    def save_data(self):
        main_screen = App.get_running_app().root.get_screen('main')
        main_screen.save_data()

class FeverApp(App):
    def build(self):
        self.title = 'Калькулятор жаропонижающих'
        sm = ScreenManager()
        
        main_screen = MainScreen(name='main')
        sm.add_widget(main_screen)
        
        return sm

if __name__ == '__main__':
    FeverApp().run()