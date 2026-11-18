INSERT INTO public.salon (nombre, capacidad, estado, ubicacion)
SELECT v.nombre, 20, 'disponible', v.ubicacion
FROM (
    VALUES
        ('Salon1', 'Sede:CLS Edificio:O'),
        ('Salon2', 'Sede:CLS Edificio:O'),
        ('Salon3', 'Sede:CLS Edificio:O'),
        ('Salon4', 'Sede:CLS Edificio:O'),
        ('Salon5', 'Sede:CLS Edificio:O'),
        ('Salon6', 'Sede:CLS Edificio:O'),
        ('Salon7', 'Sede:CLS Edificio:O'),
        ('Salon8', 'Sede:CLS Edificio:O'),
        ('Salon9', 'Sede:CLS Edificio:O'),
        ('Salon10', 'Sede:CLS Edificio:O'),
        ('Lab1', 'Sede:CLS Edificio:O'),
        ('Lab2', 'Sede:CLS Edificio:O'),
        ('Lab3', 'Sede:CLS Edificio:O'),
        ('Lab4', 'Sede:CLS Edificio:O'),
        ('Lab5', 'Sede:CLS Edificio:O'),
        ('Lab6', 'Sede:CLS Edificio:O'),
        ('Lab7', 'Sede:CLS Edificio:O'),
        ('Lab8', 'Sede:CLS Edificio:O'),
        ('Lab9', 'Sede:CLS Edificio:O'),
        ('Lab10', 'Sede:CLS Edificio:O')
) AS v(nombre, ubicacion)
WHERE NOT EXISTS (
    SELECT 1 FROM public.salon s WHERE lower(s.nombre) = lower(v.nombre)
);
