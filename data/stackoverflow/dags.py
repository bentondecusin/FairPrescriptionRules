DAG = [
    'Continent;',
    'HoursComputer;',
    'UndergradMajor;',
    'FormalEducation;',
    'Age;',
    'Gender;',
    'Dependents;',
    'Country;',
    'DevType;',
    'RaceEthnicity;',
    'ConvertedSalary;',
    'HDI;',
    'GINI;',
    'GDP;',
    'HDI -> GINI;',
    'GINI -> ConvertedSalary;',
    'GINI -> GDP;',
    'GDP -> ConvertedSalary;',
    'Gender -> FormalEducation;',
    'Gender -> UndergradMajor;',
    'Gender -> DevType;',
    'Gender -> ConvertedSalary;',
    'Country -> ConvertedSalary;',
    'Country -> FormalEducation;',
    'Country -> RaceEthnicity;',
    'Continent -> Country ;',

    'FormalEducation -> DevType;',
    'FormalEducation -> UndergradMajor;',

    'Continent -> UndergradMajor;',
    'Continent -> FormalEducation;',
    'Continent -> RaceEthnicity;',
    'Continent -> ConvertedSalary;',

    'RaceEthnicity -> ConvertedSalary;',
    'UndergradMajor -> DevType;',

    'DevType -> ConvertedSalary;',
    'DevType -> HoursComputer;',
    'Age -> ConvertedSalary;',
    'Age -> DevType;',
    'Age -> Dependents;',
    'Age -> FormalEducation;',

    'Dependents -> HoursComputer;',
    'HoursComputer -> ConvertedSalary;',]