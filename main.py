import asyncio
from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
import pandas as pd
import io
import sys
import buttons as kb
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
import config

form_router = Router()
dp = Dispatcher()
bot = Bot(token = config.TOKEN, parse_mode=ParseMode.HTML) 



class Lab(StatesGroup):
    group = State()

@form_router.message(CommandStart())
async def command_start(message: Message):
    await message.answer("Я - учебный бот, анализирующий данные из Excel по группам и их оценкам. Отправьте файл и <b>подождите</b>, пока я его обработаю")

@form_router.message(F.document)
async def get_doc(message: Message):

    doc = message.document.file_id
    print(doc) #получение ID файла, который скинули в бот, чтобы не загружать его повторно
    await message.answer('<b>Подождите несколько секунд. Файл загружается...</b>')
    file = await bot.get_file(doc)
    file_path = file.file_path
    my_object = io.BytesIO()
    MyBinaryIO = await bot.download_file(file_path, my_object)
    print(MyBinaryIO)

    global studentFGSmarks #глобальная переменная, в которой хранится датафрейм с таблицей Excel
    
    try:
        studentFGSmarks = pd.read_excel(MyBinaryIO)
    except ValueError:
        await message.answer(f'Похоже, вы загрузили файл, отличный от Excel') 
    else:
        print(studentFGSmarks)
        await message.answer('Файл получен. Воспользуйтесь кнопками, чтобы дать мне задачу.', reply_markup=kb.main)

@form_router.message(F.text == 'Показать список всех групп')

async def report(message: Message):
    columns = list(studentFGSmarks.columns.values)
    if 'Группа' and 'Год' and 'Уровень контроля' and 'Личный номер студента' in columns:
        groups = studentFGSmarks['Группа'].unique()
        listGroup = ', '.join(groups)
        await message.answer(f'В датасете содержатся оценки следующих групп: {listGroup}', reply_markup=kb.main)
    else:
        await message.answer(f'ОШИБКА! Файл не может быть обработан из-за ошибки в его структуре!')
        print('ОШИБКА пользователя: нет нужных элементов в структуре таблицы Excel!') 


@form_router.message(F.text == 'Выбрать группу')
async def report(message: Message, state: FSMContext) -> None:
    await state.set_state(Lab.group)
    await message.answer("Введите номер группы:", reply_markup=ReplyKeyboardRemove())

@form_router.message(Lab.group)

async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(group = message.text)
    await message.answer(f'Вы выбрали группу  {html.quote(message.text)}')
    whatGroup = studentFGSmarks['Группа'].str.contains(str(message.text)).sum()
    if whatGroup == 0:
        await message.answer(f'Кажется, такой группы нет в данном документе', reply_markup=kb.main)
        print('ОШИБКА пользователя: выбранной группы НЕТ в полученном документе!')
    else:
        await message.answer(f'Вывести данные о группе {html.quote(message.text)}?', reply_markup=kb.report1)

@dp.callback_query(F.data == 'report')
async def cbquantity(callback: CallbackQuery, state: FSMContext):
    choosedGroup = await state.get_data()
    marksChoosedGroup = studentFGSmarks.shape[0]
    marksCount = len(studentFGSmarks[studentFGSmarks['Группа'] == choosedGroup['group']])
    studentCount = studentFGSmarks.loc[studentFGSmarks['Группа'] == choosedGroup['group'], 'Личный номер студента'].nunique()
    personalIDStudentsGroup = studentFGSmarks.loc[studentFGSmarks['Группа'] == choosedGroup['group'], 'Личный номер студента'].unique()
    id_stud_pi101 = ", ".join(map(str, personalIDStudentsGroup))
    mass_forms_control = studentFGSmarks.loc[studentFGSmarks['Группа'] == choosedGroup['group'], 'Уровень контроля'].unique()
    forms_control = ", ".join(mass_forms_control)
    all_years1 = studentFGSmarks.loc[studentFGSmarks['Группа'] == choosedGroup['group'],'Год'].unique()
    all_years = ", ".join(map(str, all_years1))
    await callback.message.answer(f'В исходном датасете содержалось ' + marksChoosedGroup + ' оценок, из них ' + marksCount + 'относятся к группе' + choosedGroup)
    await callback.message.answer(f'В датасете находятся оценки {studentCount} студентов со следующими личными номерами: {id_stud_pi101}')
    await callback.message.answer(f'Используемые формы контроля: {forms_control}')
    await callback.message.answer(f'Данные представлены по следующим учебным годам: {all_years}')
    await callback.message.answer(f'<b> Чтобы вывести отчёт уже по другой группе, воспользуйтесь кнопками</b>', reply_markup=kb.main)

async def main():
    bot = Bot(token = config.TOKEN, parse_mode=ParseMode.HTML)
    dp.include_router(form_router)
    await dp.start_polling(bot) #проверка ТГ на наличие новых событий

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())