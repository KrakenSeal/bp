import warnings
import json
import os
from keras.models import load_model
import numpy as np

warnings.filterwarnings("ignore")  # Hide messy Numpy warnings


class baseModel(object):
    config = None
    filename = 'abstract.h5'
    name = 'abstract'
    model = None
    model_filepath = ''
    model_data = None

    steps_per_epoch = 0
    validation_steps = 0
    epochs = 0
    x_window=100
    y_widnow=1
    refresh = False
    history = None

    def __init__(self, model_filepath, data,steps_per_epoch = 0,epochs = 1,refresh = False,x_window=100,y_window=1):
        super(baseModel, self).__init__()
        print('> Инициализируем модель сети  ' + self.name)
        self.model_filepath = model_filepath
        self.model_data = data
        self.steps_per_epoch = steps_per_epoch
        self.epochs = epochs
        self.filename = self.model_filepath + self.name + ".h5"
        self.refresh = refresh
        self.x_window = x_window
        self.y_widnow = y_window
        if steps_per_epoch == 0:
            self.steps_per_epoch = int(data.ntrain /epochs / data.batch_size)
        self.validation_steps = int(data.ntest /epochs / data.batch_size)
        # self.validation_steps = int(data.ntest / data.batch_size)

    def train_network(self):
        if (not self.refresh and os.path.isfile(self.filename)):
            print('> Сеть уже натренирована, просто загружаем её из файла')
            self.__load_network();
        else:
            print('> Стартуем тренировку')
            self.__fit_model_threaded()
            print('> Готово')


    def get_network(self):
        if (not self.refresh and os.path.isfile(self.filename)):
            return self.__load_network()
        else:
            return self.__fit_model_threaded()
            # return self.build_network()


    def build_network(self):
        print('> Собираем ' + self.name + ' модель сети')
        return None

    def __load_network(self):
        # Load the h5 saved model and weights
        print('> Загружаем ' + self.name + ' модель сети')
        if (os.path.isfile(self.filename)):
            self.model = load_model(self.filename)
            return self.model
        else:
            print('ОШИБКА: "' + self.filename + '" Файл не содержит h5 модель\n')
            return None

    # Ничем не отличается от той, с которой работаю сейчас, оставил просто как пример того, как было исходно
    def __fit_model_threaded_old(self):
        print('> Тренируем модель ' + self.name)
        self.model = self.build_network()
        output_file = self.filename
        print('> Параметры модели epochs =  ' + str(self.epochs) + ' Шагов за эпоху = ' + str(self.steps_per_epoch))
        self.history = self.model.fit_generator(
            self.model_data.get_generator_clean_data(),
            steps_per_epoch=self.steps_per_epoch,
            epochs=self.epochs
        )
        self.model.save(output_file)
        print('> Модель создана! веса сохранены ', output_file)
        return self.model

    def __fit_model_threaded(self):
        print('> Тренируем модель ' + self.name)
        self.model = self.build_network()
        output_file = self.filename
        print('> Информация по данным nrows =  ' + str(self.model_data.nrows) + ' ntrain = ' + str(self.model_data.ntrain) + ' ntest = ' + str(self.model_data.ntest))
        print('> Параметры модели epochs =  ' + str(self.epochs) + ' Шагов за эпоху = ' + str(self.steps_per_epoch) + ' validation steps ' + str(self.validation_steps))
        self.history = self.model.fit_generator(
            self.model_data.get_generator_clean_data(),
            steps_per_epoch=self.steps_per_epoch,
            epochs=self.epochs,
            validation_data=self.model_data.get_generator_clean_data_test(),
            validation_steps=self.validation_steps
        )
        self.model.save(output_file)
        print('> Модель создана! веса сохранены ', output_file)
        return self.model

    # Использовать только для случая, когда y_window=1
    def get_multistep_predictions_true_data(self,steps=1):
        true_values = []
        multi_predictions=[]
        data_gen_test = self.model_data.get_generator_clean_data_test()

        steps_test = int(self.model_data.ntest / self.model_data.batch_size)
        print('> Тестируем модель на ', self.model_data.ntest, ' строках с ', steps_test, ' шагами')

        for x,y in data_gen_test:
            if len(x) == 0:
                break
            for i in range(len(x)-steps):
                true_value=[]
                multi_prediction = []
                x_curr = x[i]
                y_curr = y[i]
                for step in range(steps):
                    prediction = self.model.predict(x_curr.reshape(1,self.x_window,1))
                    # x_curr = x_curr[1:] + [prediction]
                    x_curr = x_curr[1:]
                    # x_curr.put(self.x_window-2,prediction)
                    x_curr = np.append(x_curr,prediction)
                    y_curr = y[i+step]
                    true_value.append(y_curr)
                    multi_prediction.append(prediction)
                true_values.append(true_value)
                multi_predictions.append(multi_prediction)

        return multi_prediction, true_values

    // TODO: Протестировать
    // TODO: Тщательно протестировать
    def get_predictions_true_data_with_norm(self):
        true_values = []
        norms = []

        data_gen_test = self.model_data.get_generator_clean_data_test_with_norm()

        def generator_strip_xy(data_gen, true_values):
            for x, y,n in data_gen:
                true_values += list(y)
                norms += list(n)
                yield x

        steps_test = int(self.model_data.ntest / self.model_data.batch_size)
        print('> Тестируем модель на', self.model_data.ntest, 'строках с', steps_test, 'шагами')

        predictions = self.model.predict_generator(
            generator_strip_xy(data_gen_test, true_values),
            steps=steps_test
        )

        true_values = [(a+1)*b for a,b in zip(true_values,norms)]
        predictions = [(a+1)*b for a,b in zip(predictions,norms)]
        return predictions, true_values

    def get_predictions_true_data(self):
        true_values = []

        data_gen_test = self.model_data.get_generator_clean_data_test()

        def generator_strip_xy(data_gen, true_values):
            for x, y in data_gen:
                true_values += list(y)
                yield x

        steps_test = int(self.model_data.ntest / self.model_data.batch_size)
        print('> Тестируем модель на', self.model_data.ntest, 'строках с', steps_test, 'шагами')

        predictions = self.model.predict_generator(
            generator_strip_xy(data_gen_test, true_values),
            steps=steps_test
        )

        return predictions, true_values