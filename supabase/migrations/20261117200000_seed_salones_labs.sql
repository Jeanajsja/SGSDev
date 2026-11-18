INSERT INTO public.salon (nombre, capacidad, estado, ubicacion)
SELECT v.nombre, 20, 'disponible', v.ubicacion
FROM (
    VALUES
        ('Salon1', 'Edificio principal'),
        ('Salon2', 'Edificio principal'),
        ('Salon3', 'Edificio principal'),
        ('Salon4', 'Edificio principal'),
        ('Salon5', 'Edificio principal'),
        ('Salon6', 'Edificio principal'),
        ('Salon7', 'Edificio principal'),
        ('Salon8', 'Edificio principal'),
        ('Salon9', 'Edificio principal'),
        ('Salon10', 'Edificio principal'),
        ('Lab1', 'Laboratorios'),
        ('Lab2', 'Laboratorios'),
        ('Lab3', 'Laboratorios'),
        ('Lab4', 'Laboratorios'),
        ('Lab5', 'Laboratorios'),
        ('Lab6', 'Laboratorios'),
        ('Lab7', 'Laboratorios'),
        ('Lab8', 'Laboratorios'),
        ('Lab9', 'Laboratorios'),
        ('Lab10', 'Laboratorios')
) AS v(nombre, ubicacion)
WHERE NOT EXISTS (
    SELECT 1 FROM public.salon s WHERE lower(s.nombre) = lower(v.nombre)
);
